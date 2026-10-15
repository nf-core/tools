"""Resolve merge conflicts between a pipeline and its updated TEMPLATE branch.

Merging a template update with git conflicts wherever the pipeline edited lines
next to a template change. For each conflicted file, the template's own change
(merge base -> new TEMPLATE) is split into small hunks with just enough context
to be unique, and each hunk is applied to the pipeline's version of the file
where its old text occurs exactly once. A file counts as resolved only when
every hunk applies or is already present; anything else is left for a human.

The hunk logic is adapted from nf-migrate (https://github.com/Skitionek/nf-migrate).
"""

import contextlib
import logging
import tempfile
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import git
from git import GitCommandError

log = logging.getLogger(__name__)


@dataclass
class TemplateMergeResult:
    """Outcome of merging TEMPLATE into the pipeline branch.

    Attributes:
        commit (str | None): Merge commit with every conflict resolved, or None if git merged
            cleanly by itself or some conflicts could not be resolved.
        resolved (list[str]): Conflicted files that were resolved by applying template hunks.
        unresolved (list[str]): Conflicted files that still need resolving by hand.
    """

    commit: str | None = None
    resolved: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def merge_template(repo: git.Repo, base_ref: str, template_ref: str, message: str) -> TemplateMergeResult:
    """Merge `template_ref` into `base_ref` in a temporary worktree, resolving conflicts where possible.

    The repository's own working tree and branches are left untouched; only the
    merge commit object is created when every conflict was resolved.
    """
    result = TemplateMergeResult()
    base_sha = repo.git.rev_parse("--verify", f"{base_ref}^{{commit}}")
    template_sha = repo.git.rev_parse("--verify", f"{template_ref}^{{commit}}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        worktree_path = Path(tmp_dir) / "merge"
        repo.git.worktree("add", "--detach", str(worktree_path), base_sha)
        try:
            worktree = git.Repo(worktree_path)
            # A conflicting merge exits with an error, which is what we are here to handle
            with contextlib.suppress(GitCommandError):
                worktree.git.merge("--no-ff", "--no-commit", template_sha)
            conflicted = _conflicted_files(worktree)
            if not conflicted:
                # Nothing for us to do: git merges it (or it is already up to date).
                return result

            for path in conflicted:
                resolved_text = _resolve_file(worktree, path)
                if resolved_text is None:
                    result.unresolved.append(path)
                    continue
                (worktree_path / path).write_bytes(resolved_text.encode("utf-8"))
                worktree.git.add("--", path)
                result.resolved.append(path)

            if result.unresolved:
                worktree.git.merge("--abort")
            else:
                worktree.git.commit("--no-verify", "-m", message)
                result.commit = worktree.git.rev_parse("HEAD")
        finally:
            repo.git.worktree("remove", "--force", str(worktree_path))
    return result


def _conflicted_files(worktree: git.Repo) -> list[str]:
    raw = worktree.git.diff("--name-only", "--diff-filter=U", "-z")
    return [path for path in raw.split("\0") if path]


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
