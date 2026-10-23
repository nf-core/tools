"""Turn the difference between two template commits into migration operations.

Both commits hold the nf-core template as rendered for one pipeline, as on
its TEMPLATE branch. Each changed file becomes small replacements with the
least context that keeps them unique, so a local edit a few lines away from
a template change does not make it conflict, as it would in a git merge.
"""

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from fnmatch import fnmatch

import git

from nf_core.components.constants import NF_CORE_MODULES_REMOTE
from nf_core.pipelines.template_migrations.operations import (
    CreateFile,
    DeleteFile,
    ManualStep,
    NfCoreComponent,
    Operation,
    Replace,
    find_line_aligned,
)
from nf_core.pipelines.template_migrations.version import NF_CORE_CONFIG_PATHS, parse_version, stamp_version

MODULES_JSON = "modules.json"
COMPONENT_KINDS = ("modules", "subworkflows")

# Files nf-core generates rather than templates. The RO-Crate gets fresh
# timestamps and random IDs on every render, and the container configs
# follow the installed module versions, so their changes would rarely match
# a pipeline. The migration names the command that rebuilds them instead.
GENERATED_FILE_INSTRUCTIONS = {
    "ro-crate-metadata.json": "regenerate with `nf-core pipelines rocrate`",
    "conf/containers_*.config": "regenerate with `nf-core pipelines containers create-configs`",
}


@dataclass(frozen=True, slots=True)
class FileChange:
    path: str
    is_binary: bool


@dataclass(frozen=True, slots=True)
class TemplateFile:
    content: str
    executable: bool


@dataclass(slots=True)
class Hunk:
    """Consecutive non-equal opcodes plus the context lines around them."""

    first_opcode: int
    last_opcode: int
    context_before: int = 0
    context_after: int = 0


def generate_operations(repo: git.Repo, old_ref: str, new_ref: str) -> list[Operation]:
    """Operations that turn the template at `old_ref` into the one at `new_ref`."""
    old_commit = repo.commit(old_ref)
    new_commit = repo.commit(new_ref)
    new_version = template_version(new_commit)

    old_components = _component_shas(_read(old_commit, MODULES_JSON))
    new_components = _component_shas(_read(new_commit, MODULES_JSON))
    changed_components = {
        component
        for component in old_components.keys() | new_components.keys()
        if old_components.get(component) != new_components.get(component)
    }
    known_components = old_components.keys() | new_components.keys()

    operations: list[Operation] = []
    generated_file_patterns: set[str] = set()
    for change in _changed_files(repo, old_ref, new_ref):
        # modules.json follows the component updates below.
        if change.path == MODULES_JSON:
            continue
        component = _component_for_path(change.path, known_components)
        if component is not None:
            changed_components.add(component)
            continue
        pattern = _generated_file_pattern(change.path)
        if pattern is not None:
            generated_file_patterns.add(pattern)
            continue
        operations.extend(_operations_for_change(old_commit, new_commit, change, new_version))

    for kind, name in sorted(changed_components):
        operations.append(NfCoreComponent(kind, name, git_sha=new_components.get((kind, name))))
    for pattern in sorted(generated_file_patterns):
        operations.append(ManualStep(pattern, GENERATED_FILE_INSTRUCTIONS[pattern]))
    return operations


def _operations_for_change(
    old_commit: git.Commit, new_commit: git.Commit, change: FileChange, new_version: str | None
) -> list[Operation]:
    if change.is_binary:
        return [ManualStep(change.path, "binary file changed in the template; copy it by hand")]

    old_file = _read(old_commit, change.path)
    new_file = _read(new_commit, change.path)
    if old_file is None:
        # git only lists a file that one of the two commits has.
        assert new_file is not None
        return [CreateFile(change.path, content=new_file.content, executable=new_file.executable)]
    if new_file is None:
        return [DeleteFile(change.path, expected_content=old_file.content)]

    old_text = old_file.content
    # The version stamp is set separately; diffing that line too would tie
    # the change to whatever surrounds it in each pipeline's .nf-core.yml.
    if change.path in NF_CORE_CONFIG_PATHS and new_version is not None:
        old_text = stamp_version(old_text, new_version)

    return [Replace(change.path, old=old, new=new) for old, new in diff_hunks(old_text, new_file.content)]


def template_version(commit: git.Commit) -> str | None:
    """The nf_core_version recorded in a commit's .nf-core.yml (or .nf-core.yaml)."""
    for config_path in NF_CORE_CONFIG_PATHS:
        config = _read(commit, config_path)
        if config is not None:
            return parse_version(config.content)
    return None


def diff_hunks(old_text: str, new_text: str) -> list[tuple[str, str]]:
    """Split a file diff into (old, new) blocks with minimal unique context.

    A replacement whose changed lines are unique needs no context.
    Insertions and deletions keep at least one line, since without it an
    applied change cannot be told from a missing one.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    opcodes = SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes()

    hunks = [Hunk(index, index) for index, opcode in enumerate(opcodes) if opcode[0] != "equal"]
    hunks = _choose_unique_context(hunks, opcodes, old_text, new_text)
    hunks = _merge_overlapping(hunks, opcodes)
    return [_hunk_blocks(hunk, opcodes, old_lines, new_lines) for hunk in hunks]


def _choose_unique_context(hunks: list[Hunk], opcodes: list, old_text: str, new_text: str) -> list[Hunk]:
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    index = 0
    while index < len(hunks):
        hunk = hunks[index]
        max_before = _equal_length(opcodes, hunk.first_opcode - 1)
        max_after = _equal_length(opcodes, hunk.last_opcode + 1)

        is_replacement = opcodes[hunk.first_opcode][0] == opcodes[hunk.last_opcode][0] == "replace"
        first_context = 0 if is_replacement else 1
        found_unique_context = False
        for context in range(first_context, max(max_before, max_after, 1) + 1):
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
                hunks[index : index + 2] = [Hunk(hunk.first_opcode, hunks[index + 1].last_opcode)]
            else:
                hunks[index - 1 : index + 1] = [Hunk(hunks[index - 1].first_opcode, hunk.last_opcode)]
                index -= 1
            continue
        index += 1
    return hunks


def _merge_overlapping(hunks: list[Hunk], opcodes: list) -> list[Hunk]:
    merged: list[Hunk] = []
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


def _hunk_blocks(hunk: Hunk, opcodes: list, old_lines: list[str], new_lines: list[str]) -> tuple[str, str]:
    _, old_start, _, new_start, _ = opcodes[hunk.first_opcode]
    _, _, old_end, _, new_end = opcodes[hunk.last_opcode]
    old_block = old_lines[old_start - hunk.context_before : old_end + hunk.context_after]
    new_block = new_lines[new_start - hunk.context_before : new_end + hunk.context_after]
    return "".join(old_block), "".join(new_block)


def _equal_length(opcodes: list, index: int) -> int:
    """Length of the equal block next to a hunk, 0 at the start or end of the file.

    SequenceMatcher alternates equal and non-equal opcodes, so the neighbour
    of a change is always an equal block.
    """
    if index < 0 or index >= len(opcodes):
        return 0
    _, old_start, old_end, _, _ = opcodes[index]
    return old_end - old_start


def _is_unique(text: str, block: str) -> bool:
    if not block:
        return False
    return len(find_line_aligned(text, block)) == 1


def _component_shas(modules_json: TemplateFile | None) -> dict[tuple[str, str], str]:
    """(kind, name) -> git_sha for the nf-core components in modules.json."""
    if modules_json is None:
        return {}
    repos = json.loads(modules_json.content).get("repos", {})
    nf_core_repo = repos.get(NF_CORE_MODULES_REMOTE, {})

    shas: dict[tuple[str, str], str] = {}
    for kind in COMPONENT_KINDS:
        components = nf_core_repo.get(kind, {}).get("nf-core", {})
        for name, entry in components.items():
            shas[(kind, name)] = entry.get("git_sha")
    return shas


def _component_for_path(path: str, known_components: set[tuple[str, str]]) -> tuple[str, str] | None:
    """The nf-core module or subworkflow a file belongs to, if any."""
    for kind in COMPONENT_KINDS:
        prefix = f"{kind}/nf-core/"
        if not path.startswith(prefix):
            continue
        # Longest known name first: samtools/sort before samtools.
        names = sorted((name for known_kind, name in known_components if known_kind == kind), key=len, reverse=True)
        for name in names:
            if path.startswith(f"{prefix}{name}/"):
                return (kind, name)
        # Not in either modules.json: fall back to the first path segment.
        return (kind, path[len(prefix) :].split("/", 1)[0])
    return None


def _generated_file_pattern(path: str) -> str | None:
    for pattern in GENERATED_FILE_INSTRUCTIONS:
        if fnmatch(path, pattern):
            return pattern
    return None


def _changed_files(repo: git.Repo, old_ref: str, new_ref: str) -> list[FileChange]:
    numstat = repo.git.diff("--no-renames", "--numstat", "-z", old_ref, new_ref)
    changes: list[FileChange] = []
    for entry in numstat.split("\0"):
        if not entry:
            continue
        added, _, path = entry.split("\t", 2)
        changes.append(FileChange(path, is_binary=added == "-"))
    return changes


def _read(commit: git.Commit, path: str) -> TemplateFile | None:
    """A file's exact content and executable bit in `commit`, or None if it is not there."""
    try:
        blob = commit.tree / path
    except KeyError:
        return None
    content = blob.data_stream.read().decode("utf-8")
    return TemplateFile(content, executable=bool(blob.mode & 0o111))
