"""Resolve merge conflicts between a pipeline and its updated TEMPLATE branch.

Merging a template update with git conflicts wherever the pipeline edited lines
next to a template change. Conflicts are resolved in this order:

1. Files with a fixed rule: generated files and nf-core components keep the
   pipeline's version and are regenerated or updated after the merge.
2. Every other file: the template's own change (merge base -> new TEMPLATE) is
   split into small hunks with just enough context to be unique, and each hunk
   is applied to the pipeline's version of the file where its old text occurs
   exactly once. A file counts as resolved only when every hunk applies or is
   already present.

If anything is left, or a resolved Nextflow file gains `nextflow lint` errors,
the merge is discarded and left for a human.

The hunk logic is adapted from nf-migrate (https://github.com/Skitionek/nf-migrate).
"""

import contextlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from itertools import takewhile
from pathlib import Path

import git
import yaml
from git import GitCommandError
from packaging.version import InvalidVersion, Version

from nf_core.components.constants import NF_CORE_MODULES_REMOTE

log = logging.getLogger(__name__)

TEMPLATE_COMMIT_SUBJECT = re.compile(r"^Template update for nf-core/tools version (\S+)$")
GENERATED_FILES = re.compile(r"^(ro-crate-metadata\.json|conf/containers_[^/]+\.config)$")
# Lint redraws the logos with local fonts, so the template's copy is no more correct than the pipeline's.
LOGO_FILES = re.compile(r"^(assets|docs/images)/nf-core-[^/]*_logo[^/]*\.png$")
COMPONENT_FILES = re.compile(r"^(modules\.json$|(modules|subworkflows)/nf-core/)")
NF_CORE_VERSION_LINE = re.compile(r"^nf_core_version:.*$", re.MULTILINE)


@dataclass
class TemplateMergeResult:
    """Outcome of merging TEMPLATE into the pipeline branch.

    Attributes:
        commit (str | None): Tip of the merge with every conflict resolved (the merge commit plus any
            regeneration commits), or None if git merged cleanly by itself or some conflicts could not be resolved.
        conflicts (list[str]): Files that a plain `git merge` of the template conflicts in.
        resolved (list[str]): Conflicted files that were resolved by applying template hunks.
        by_rule (dict[str, str]): Conflicted files resolved by a fixed rule, with what was done.
        unresolved (list[str]): Conflicted files that still need resolving by hand.
        regenerated (list[str]): What the commits after the merge commit did.
        todo (list[str]): Commands that failed after the merge and need running by hand.
        warnings (list[str]): Things a reviewer needs to know about the merge.
    """

    commit: str | None = None
    conflicts: list[str] = field(default_factory=list)
    resolved: list[str] = field(default_factory=list)
    by_rule: dict[str, str] = field(default_factory=dict)
    unresolved: list[str] = field(default_factory=list)
    regenerated: list[str] = field(default_factory=list)
    todo: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class _Component:
    kind: str
    name: str
    path: str
    sha: str


def merge_template(
    repo: git.Repo, base_ref: str, template_ref: str, message: str, regenerate: bool = True
) -> TemplateMergeResult:
    """Merge `template_ref` into `base_ref` in a temporary worktree, resolving conflicts where possible.

    The repository's own working tree and branches are left untouched; only the
    commit objects are created when every conflict was resolved.
    """
    result = TemplateMergeResult()
    base_sha = repo.git.rev_parse("--verify", f"{base_ref}^{{commit}}")
    template_sha = repo.git.rev_parse("--verify", f"{template_ref}^{{commit}}")
    if repo.is_ancestor(template_sha, base_sha):
        return result

    with tempfile.TemporaryDirectory() as tmp_dir:
        worktree_path = Path(tmp_dir) / "merge"
        repo.git.worktree("add", "--detach", str(worktree_path), base_sha)
        try:
            worktree = git.Repo(worktree_path)
            merge_error = None
            try:
                worktree.git.merge("--no-ff", "--no-commit", template_sha)
            except GitCommandError as e:
                merge_error = e
            result.conflicts = _conflicted_files(worktree)
            if not result.conflicts:
                if merge_error is not None:
                    raise merge_error
                return result

            stale_base = _stale_template_base(repo, base_sha, template_sha, result)
            if stale_base:
                _remerge(worktree, stale_base, base_sha, template_sha)
            conflicted = _conflicted_files(worktree)

            components = _apply_rules(worktree, conflicted, base_sha, template_sha, result)
            for path in _conflicted_files(worktree):
                resolved_text = _resolve_file(worktree, path)
                if resolved_text is None:
                    result.unresolved.append(path)
                    continue
                (worktree_path / path).write_bytes(resolved_text.encode("utf-8"))
                worktree.git.add("--", path)
                result.resolved.append(path)
            if result.unresolved:
                worktree.git.merge("--abort")
                return result

            worktree.git.commit("--no-verify", "-m", message)

            lint_failures = _new_lint_errors(worktree, base_sha, result.resolved)
            if lint_failures is None:
                result.unresolved = [p for p in result.resolved if p.endswith((".nf", ".config"))]
                result.warnings.append("`nextflow lint` could not run, so the automatic resolution was not used.")
                return result
            if lint_failures:
                result.unresolved = lint_failures
                result.warnings.append(
                    "Applying the template changes gave these files new `nextflow lint` errors, "
                    "so the automatic resolution was not used: " + ", ".join(f"`{p}`" for p in lint_failures)
                )
                return result

            if regenerate:
                _regenerate(worktree, components, conflicted, result)
            result.commit = worktree.head.commit.hexsha
        finally:
            repo.git.worktree("remove", "--force", str(worktree_path))
    return result


def _conflicted_files(worktree: git.Repo) -> list[str]:
    raw = worktree.git.diff("--name-only", "--diff-filter=U", "-z")
    return sorted({path for path in raw.split("\0") if path})


def _template_version(repo: git.Repo, ref: str) -> str | None:
    """Version of the newest template commit in the history of `ref`."""
    for subject in repo.git.log("--format=%s", ref).splitlines():
        match = TEMPLATE_COMMIT_SUBJECT.match(subject)
        if match:
            return match.group(1)
    return None


def _tools_config(repo: git.Repo, ref: str) -> dict:
    for name in (".nf-core.yml", ".nf-core.yaml"):
        with contextlib.suppress(GitCommandError):
            return yaml.safe_load(repo.git.show(f"{ref}:{name}")) or {}
    return {}


def _stale_template_base(repo: git.Repo, base_sha: str, template_sha: str, result: TemplateMergeResult) -> str | None:
    """The TEMPLATE commit to use as merge base when the git merge base is older than the pipeline's template.

    After a squash-merged or hand-made template update, `.nf-core.yml` names a newer template than the
    git history holds, and merging from the old base conflicts on changes the pipeline already has.
    """
    git_version = _template_version(repo, repo.git.merge_base(base_sha, template_sha))
    stamped = _tools_config(repo, base_sha).get("nf_core_version")
    try:
        if not git_version or not stamped or Version(str(stamped)) <= Version(git_version):
            return None
    except InvalidVersion:
        return None

    candidate = None
    for line in repo.git.log("--format=%H %s", template_sha).splitlines():
        sha, _, subject = line.partition(" ")
        match = TEMPLATE_COMMIT_SUBJECT.match(subject)
        if match and match.group(1) == str(stamped):
            candidate = sha
            break
    if candidate is None or repo.git.version_info < (2, 40):
        result.warnings.append(
            f"`.nf-core.yml` says template {stamped}, but the git history only contains template {git_version}, "
            "for example after a squash-merged template update. Expect more conflicts than usual."
        )
        return None
    result.warnings.append(
        f"`.nf-core.yml` says template {stamped}, but the git history only contains template {git_version}, "
        f"for example after a squash-merged template update. The merge used the TEMPLATE {stamped} commit as its base."
    )
    return candidate


def _remerge(worktree: git.Repo, merge_base: str, base_sha: str, template_sha: str) -> None:
    """Replace the merge in progress with one from `merge_base`, keeping MERGE_HEAD so it still commits as a merge."""
    proc = subprocess.run(
        ["git", "merge-tree", "--write-tree", f"--merge-base={merge_base}", base_sha, template_sha],
        cwd=worktree.working_dir,
        capture_output=True,
        text=True,
    )
    # Exit code 1 means conflicts, which are expected
    if proc.returncode not in (0, 1):
        raise GitCommandError(proc.args, proc.returncode, proc.stderr)
    lines = proc.stdout.splitlines()
    stages = list(takewhile(bool, lines[1:]))
    worktree.git.read_tree("--reset", "-u", lines[0])
    if stages:
        paths = sorted({stage.split("\t", 1)[1] for stage in stages})
        # A zero-mode entry removes stage 0, so that the conflict stages can be added
        index_info = "".join(f"0 {'0' * 40}\t{path}\n" for path in paths) + "".join(f"{s}\n" for s in stages)
        subprocess.run(
            ["git", "update-index", "--index-info"], input=index_info, text=True, cwd=worktree.working_dir, check=True
        )


def _has_stage(worktree: git.Repo, stage: int, path: str) -> bool:
    return bool(worktree.git.ls_files("--stage", "--", path).count(f" {stage}\t"))


def _exists_at(worktree: git.Repo, ref: str, path: str) -> bool:
    return bool(worktree.git.ls_tree(ref, "--", path))


def _nf_core_components(worktree: git.Repo, ref: str) -> dict[str, _Component]:
    """nf-core modules and subworkflows that `modules.json` at `ref` lists, by path."""
    try:
        modules_json = json.loads(worktree.git.show(f"{ref}:modules.json"))
    except (GitCommandError, json.JSONDecodeError):
        return {}
    repo = modules_json.get("repos", {}).get(NF_CORE_MODULES_REMOTE, {})
    components = {}
    for kind in ("modules", "subworkflows"):
        for name, info in repo.get(kind, {}).get("nf-core", {}).items():
            path = f"{kind}/nf-core/{name}"
            components[path] = _Component(kind, name, path, info.get("git_sha", ""))
    return components


def _apply_rules(
    worktree: git.Repo, conflicted: list[str], base_sha: str, template_sha: str, result: TemplateMergeResult
) -> list[_Component]:
    """Resolve the conflicts that have a fixed rule. Returns the components to update to the template version."""
    for path in conflicted:
        if GENERATED_FILES.match(path) or LOGO_FILES.match(path):
            if _has_stage(worktree, 2, path):
                worktree.git.checkout("--ours", "--", path)
                worktree.git.add("--", path)
            else:
                worktree.git.rm("-q", "--", path)
            result.by_rule[path] = "kept the pipeline's version" + (
                "; regenerated below" if GENERATED_FILES.match(path) else ""
            )
        elif path == "CHANGELOG.md" and _has_stage(worktree, 2, path):
            # The template's changelog is a placeholder for new pipelines
            worktree.git.checkout("--ours", "--", path)
            worktree.git.add("--", path)
            result.by_rule[path] = "kept the pipeline's version"
        elif path in (".nf-core.yml", ".nf-core.yaml"):
            pipeline, template = _read_stage(worktree, 2, path), _read_stage(worktree, 3, path)
            template_line = NF_CORE_VERSION_LINE.search(template or "")
            if pipeline is None or template_line is None or not NF_CORE_VERSION_LINE.search(pipeline):
                continue
            Path(worktree.working_dir, path).write_text(
                NF_CORE_VERSION_LINE.sub(template_line.group(0), pipeline, count=1)
            )
            worktree.git.add("--", path)
            result.by_rule[path] = "kept the pipeline's version with the template's `nf_core_version`"

    if not any(COMPONENT_FILES.match(path) for path in conflicted) or not _exists_at(
        worktree, base_sha, "modules.json"
    ):
        return []

    # Restoring every template component from the pipeline keeps modules.json consistent with the files.
    template_components = _nf_core_components(worktree, template_sha)
    base_components = _nf_core_components(worktree, base_sha)
    _restore_from(worktree, base_sha, "modules.json")
    result.by_rule["modules.json"] = "kept the pipeline's version; template modules and subworkflows updated below"
    to_update = []
    for path, component in sorted(template_components.items()):
        _restore_from(worktree, base_sha, path)
        if path not in base_components:
            result.by_rule[f"{path}/"] = "kept the pipeline's deletion"
        elif base_components[path].sha != component.sha:
            to_update.append(component)
    return to_update


def _restore_from(worktree: git.Repo, ref: str, path: str) -> None:
    """Make the file or directory `path` match `ref`, conflicts included, deleting it if `ref` lacks it."""
    worktree.git.rm("-r", "-q", "-f", "--cached", "--ignore-unmatch", "--", path)
    target = Path(worktree.working_dir, path)
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink(missing_ok=True)
    if _exists_at(worktree, ref, path):
        worktree.git.checkout(ref, "--", path)


def _new_lint_errors(worktree: git.Repo, base_sha: str, files: list[str]) -> list[str] | None:
    """Hunk-resolved Nextflow files with `nextflow lint` errors that the pipeline's version does not have.

    Returns None if `nextflow lint` could not run.
    """
    files = [path for path in files if path.endswith((".nf", ".config"))]
    if not files:
        return []
    after = _lint_errors(worktree, files)
    if after is None:
        return None
    if not after:
        return []
    worktree.git.checkout(base_sha, "--", *files)
    before = _lint_errors(worktree, files) or set()
    worktree.git.checkout("HEAD", "--", *files)
    return sorted({path for path, _ in after - before})


def _lint_errors(worktree: git.Repo, files: list[str]) -> set[tuple[str, str]] | None:
    try:
        proc = subprocess.run(
            ["nextflow", "lint", "-o", "json", *files],
            cwd=worktree.working_dir,
            capture_output=True,
            text=True,
            timeout=600,
        )
        report = json.loads(proc.stdout[proc.stdout.find("{") :])
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    return {(error["filename"], error["message"]) for error in report.get("errors", [])}


def _commit_paths(worktree: git.Repo, message: str, *paths: str) -> bool:
    worktree.git.add("-A", "--", *paths)
    if not worktree.git.diff("--cached", "--name-only"):
        return False
    worktree.git.commit("--no-verify", "-m", message)
    return True


def _regenerate(
    worktree: git.Repo, components: list[_Component], conflicted: list[str], result: TemplateMergeResult
) -> None:
    """Update the template components and regenerate the generated files, one commit each.

    A failed step is reported in `result.todo` rather than failing the merge: the merge is already
    correct, it only lacks the template's versions of these files.
    """
    from nf_core.pipelines.containers_utils import ContainerConfigs
    from nf_core.pipelines.rocrate import ROCrate

    path = Path(worktree.working_dir)
    updated = _update_components(worktree, components, result)
    if updated:
        _commit_paths(
            worktree, "Update nf-core template modules and subworkflows", "modules.json", "modules", "subworkflows"
        )
        # `modules update` rewrites the container configs with only the updated modules
        with contextlib.suppress(GitCommandError):
            worktree.git.checkout("HEAD", "--", "conf")
        worktree.git.clean("-fdq", "--", "conf")

    if (
        (updated or any(p.startswith("conf/containers_") for p in conflicted))
        and worktree.git.ls_files("--", "conf/containers_*.config")
        and (_tools_config(worktree, "HEAD").get("lint") or {}).get("container_configs") is not False
    ):
        try:
            ContainerConfigs(path).generate_container_configs()
            if _commit_paths(worktree, "Regenerate container configs", "conf"):
                result.regenerated.append("Regenerated the `conf/containers_*.config` files")
        except Exception as e:  # noqa: BLE001
            log.debug(f"Could not regenerate container configs: {e}")
            worktree.git.checkout("HEAD", "--", "conf")
            result.todo.append("`nf-core pipelines lint --fix container_configs`")

    if "ro-crate-metadata.json" in conflicted and (path / "ro-crate-metadata.json").exists():
        try:
            ROCrate(path).create_rocrate(json_path=path)
            if _commit_paths(worktree, "Regenerate RO-Crate metadata", "ro-crate-metadata.json"):
                result.regenerated.append("Regenerated `ro-crate-metadata.json`")
        except Exception as e:  # noqa: BLE001
            log.debug(f"Could not regenerate the RO-Crate: {e}")
            worktree.git.checkout("HEAD", "--", "ro-crate-metadata.json")
            result.todo.append("`nf-core pipelines rocrate . --json_path .`")


def _update_components(worktree: git.Repo, components: list[_Component], result: TemplateMergeResult) -> bool:
    """Update each component to the template version, unless the pipeline already has a newer one."""
    from nf_core.modules.update import ModuleUpdate
    from nf_core.subworkflows.update import SubworkflowUpdate

    path = Path(worktree.working_dir)
    updated = False
    for component in components:
        command = f"`nf-core {component.kind} update {component.name} --sha {component.sha}`"
        component_dir = path / component.path
        had_tests = (component_dir / "tests").exists()
        try:
            update_class = ModuleUpdate if component.kind == "modules" else SubworkflowUpdate
            updater = update_class(path, sha=component.sha, show_diff=False, skip_deps=True)
            base_sha = updater.modules_json.get_component_version(
                component.kind, component.name, NF_CORE_MODULES_REMOTE, "nf-core"
            )
            if base_sha and not updater.current_remote.repo.is_ancestor(base_sha, component.sha):
                continue
            # Lock files from the old version would otherwise be left behind
            shutil.rmtree(component_dir / ".conda-lock", ignore_errors=True)
            if not updater.update(component.name):
                raise UserWarning("update returned False")
        except Exception as e:  # noqa: BLE001
            log.debug(f"Could not update {component.kind} {component.name}: {e}")
            worktree.git.checkout("HEAD", "--", "modules.json", component.path)
            worktree.git.clean("-fdq", "--", component.path)
            result.todo.append(command)
            continue
        if not had_tests:
            shutil.rmtree(component_dir / "tests", ignore_errors=True)
        result.regenerated.append(f"Updated `{component.name}` to the template version")
        updated = True
    return updated


def _resolve_file(worktree: git.Repo, path: str) -> str | None:
    """The pipeline's version of `path` with the template's changes applied, or None."""
    # Index stages of a conflicted file: 1 = merge base, 2 = ours (pipeline), 3 = theirs (TEMPLATE).
    # A missing stage means an add/add or modify/delete conflict, which needs a human decision.
    old_template, pipeline, new_template = (_read_stage(worktree, stage, path) for stage in (1, 2, 3))
    if old_template is None or pipeline is None or new_template is None:
        return None

    content = pipeline
    for old, new in diff_hunks(old_template, new_template):
        applied = apply_hunk(content, old, new)
        if applied is None:
            return None
        content = applied
    return content


def _read_stage(worktree: git.Repo, stage: int, path: str) -> str | None:
    try:
        raw = worktree.git.show(f":{stage}:{path}", strip_newline_in_stdout=False, stdout_as_string=False)
    except GitCommandError:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Leave binary files alone
    return None if "\0" in text else text


def find_line_aligned(content: str, text: str) -> list[int]:
    """Start offsets where `text` occurs beginning at the start of a line.

    Without this, a hunk for "line 3" would also match inside "line 13".
    """
    positions: list[int] = []
    start = content.find(text)
    while start != -1:
        if start == 0 or content[start - 1] == "\n":
            positions.append(start)
        start = content.find(text, start + 1)
    return positions


def apply_hunk(content: str, old: str, new: str) -> str | None:
    """Replace `old` with `new` if it occurs exactly once.

    Returns the content unchanged if only `new` is present (already applied),
    and None if the hunk cannot be placed unambiguously.
    """
    if not old:
        return None
    old_positions = find_line_aligned(content, old)
    if len(old_positions) == 1:
        start = old_positions[0]
        return content[:start] + new + content[start + len(old) :]
    if not old_positions and new and find_line_aligned(content, new):
        return content
    return None


@dataclass
class _Hunk:
    """Consecutive non-equal opcodes plus the context lines around them."""

    first_opcode: int
    last_opcode: int
    context_before: int = 0
    context_after: int = 0


def diff_hunks(old_text: str, new_text: str) -> list[tuple[str, str]]:
    """Split a file diff into (old, new) blocks with minimal unique context.

    Each block keeps only as much surrounding context as it needs to occur
    exactly once in its template file, so local edits next to a template
    change do not make it conflict.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    opcodes = SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes()

    hunks = [_Hunk(index, index) for index, opcode in enumerate(opcodes) if opcode[0] != "equal"]
    hunks = _choose_unique_context(hunks, opcodes, old_text, new_text)
    hunks = _merge_overlapping(hunks, opcodes)
    return [_hunk_blocks(hunk, opcodes, old_lines, new_lines) for hunk in hunks]


def _choose_unique_context(hunks: list[_Hunk], opcodes: list, old_text: str, new_text: str) -> list[_Hunk]:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    index = 0
    while index < len(hunks):
        hunk = hunks[index]
        max_before = _equal_length(opcodes, hunk.first_opcode - 1)
        max_after = _equal_length(opcodes, hunk.last_opcode + 1)

        # Start without context: git only conflicts where the pipeline edited lines right next to a
        # template change, so any context line is likely to have been edited too.
        found_unique_context = False
        for context in range(max(max_before, max_after, 1) + 1):
            hunk.context_before = min(context, max_before)
            hunk.context_after = min(context, max_after)
            old_block, new_block = _hunk_blocks(hunk, opcodes, old_lines, new_lines)
            if _is_unique(old_text, old_block) and _is_unique(new_text, new_block):
                found_unique_context = True
                break

        # The neighbouring equal blocks are too short to make this hunk
        # unique, so grow it across them into the next or previous hunk.
        if not found_unique_context and len(hunks) > 1:
            if index + 1 < len(hunks):
                hunks[index : index + 2] = [_Hunk(hunk.first_opcode, hunks[index + 1].last_opcode)]
            else:
                hunks[index - 1 : index + 1] = [_Hunk(hunks[index - 1].first_opcode, hunk.last_opcode)]
                index -= 1
            continue
        index += 1
    return hunks


def _merge_overlapping(hunks: list[_Hunk], opcodes: list) -> list[_Hunk]:
    merged: list[_Hunk] = []
    for hunk in hunks:
        if merged:
            previous = merged[-1]
            gap = _equal_length(opcodes, previous.last_opcode + 1)
            if previous.context_after + hunk.context_before > gap:
                previous.last_opcode = hunk.last_opcode
                previous.context_after = hunk.context_after
                continue
        merged.append(hunk)
    return merged


def _hunk_blocks(hunk: _Hunk, opcodes: list, old_lines: list[str], new_lines: list[str]) -> tuple[str, str]:
    _, old_start, _, new_start, _ = opcodes[hunk.first_opcode]
    _, _, old_end, _, new_end = opcodes[hunk.last_opcode]
    old_block = old_lines[old_start - hunk.context_before : old_end + hunk.context_after]
    new_block = new_lines[new_start - hunk.context_before : new_end + hunk.context_after]
    return "".join(old_block), "".join(new_block)


def _equal_length(opcodes: list, index: int) -> int:
    if index < 0 or index >= len(opcodes):
        return 0
    tag, old_start, old_end, _, _ = opcodes[index]
    if tag != "equal":
        return 0
    return old_end - old_start


def _is_unique(text: str, block: str) -> bool:
    if not block:
        return False
    return len(find_line_aligned(text, block)) == 1
