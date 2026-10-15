"""Idempotent file operations that a template migration is made of.

Every operation inspects the pipeline before changing it and reports an
outcome. Running an operation twice is safe: the second run sees the new
text and reports ALREADY_APPLIED. Anything an operation cannot place
unambiguously is a CONFLICT for a maintainer to resolve.
"""

import difflib
import enum
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from nf_core.components.constants import NF_CORE_MODULES_REMOTE


class Outcome(enum.Enum):
    APPLIED = "applied"
    ALREADY_APPLIED = "already applied"
    CONFLICT = "conflict"
    # Work left to nf-core's own commands. Reported, never blocking.
    MANUAL = "manual step"


@dataclass(frozen=True, slots=True)
class OperationResult:
    path: str
    outcome: Outcome
    message: str = ""
    # The template change as a diff; reports show it for conflicts, so a
    # maintainer can apply it by hand.
    suggestion: str = ""


class Workspace:
    """In-memory view of a pipeline directory.

    Operations read and write here, so changes that hit a conflict can be
    dropped without having touched any file on disk.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._pending: dict[str, str | None] = {}
        self._executable: set[str] = set()

    def read(self, path: str) -> str | None:
        if path in self._pending:
            return self._pending[path]
        return self._read_from_disk(path)

    def write(self, path: str, content: str, executable: bool = False) -> None:
        self._pending[path] = content
        if executable:
            self._executable.add(path)

    def delete(self, path: str) -> None:
        self._pending[path] = None

    def snapshot(self) -> dict[str, str | None]:
        return dict(self._pending)

    def restore(self, snapshot: dict[str, str | None]) -> None:
        self._pending = dict(snapshot)

    def restore_paths(self, snapshot: dict[str, str | None], paths: set[str]) -> None:
        """Undo changes to `paths` made since `snapshot`."""
        for path in paths:
            if path in snapshot:
                self._pending[path] = snapshot[path]
            else:
                self._pending.pop(path, None)

    def changed_paths(self) -> list[str]:
        return [path for path, content in sorted(self._pending.items()) if content != self._read_from_disk(path)]

    def commit(self) -> None:
        """Write the pending changes to disk."""
        for path, content in self._pending.items():
            file_path = self.root / path
            if content is None:
                file_path.unlink(missing_ok=True)
                continue
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # newline="" keeps line endings exactly as they are, so a CRLF
            # file neither fails to match nor gets rewritten as LF.
            with file_path.open("w", encoding="utf-8", newline="") as file:
                file.write(content)
            if path in self._executable:
                file_path.chmod(file_path.stat().st_mode | 0o111)
        self._pending.clear()
        self._executable.clear()

    def _read_from_disk(self, path: str) -> str | None:
        file_path = self.root / path
        if not file_path.is_file():
            return None
        with file_path.open(encoding="utf-8", newline="") as file:
            return file.read()


def find_line_aligned(content: str, text: str) -> list[int]:
    """Start offsets where `text` occurs beginning at the start of a line.

    Without this, a change to "line 3" would also match inside "line 13".
    """
    positions: list[int] = []
    start = content.find(text)
    while start != -1:
        if start == 0 or content[start - 1] == "\n":
            positions.append(start)
        start = content.find(text, start + 1)
    return positions


def _change_diff(path: str, old: str, new: str) -> str:
    diff_lines = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff_lines)


class Operation(Protocol):
    """One change of a template migration."""

    @property
    def path(self) -> str: ...

    def apply(self, workspace: Workspace) -> OperationResult: ...


@dataclass(frozen=True, slots=True)
class Replace:
    """Replace one exact block of text, usually a template diff hunk."""

    path: str
    old: str
    new: str

    def apply(self, workspace: Workspace) -> OperationResult:
        change = _change_diff(self.path, self.old, self.new)

        content = workspace.read(self.path)
        if content is None:
            return OperationResult(self.path, Outcome.CONFLICT, "file does not exist", change)

        old_positions = find_line_aligned(content, self.old)
        if len(old_positions) == 1:
            start = old_positions[0]
            end = start + len(self.old)
            workspace.write(self.path, content[:start] + self.new + content[end:])
            return OperationResult(self.path, Outcome.APPLIED, "", change)
        if len(old_positions) > 1:
            message = f"old text found {len(old_positions)} times"
            return OperationResult(self.path, Outcome.CONFLICT, message, change)
        if self.new and find_line_aligned(content, self.new):
            return OperationResult(self.path, Outcome.ALREADY_APPLIED, "", change)
        return OperationResult(self.path, Outcome.CONFLICT, "old text not found", change)


@dataclass(frozen=True, slots=True)
class CreateFile:
    path: str
    content: str
    executable: bool = False

    def apply(self, workspace: Workspace) -> OperationResult:
        existing = workspace.read(self.path)
        if existing is None:
            workspace.write(self.path, self.content, executable=self.executable)
            return OperationResult(self.path, Outcome.APPLIED)
        if existing == self.content:
            return OperationResult(self.path, Outcome.ALREADY_APPLIED)
        return OperationResult(self.path, Outcome.CONFLICT, "file exists with different content")


@dataclass(frozen=True, slots=True)
class DeleteFile:
    """Delete a template file, but only if the pipeline left it untouched."""

    path: str
    expected_content: str

    def apply(self, workspace: Workspace) -> OperationResult:
        existing = workspace.read(self.path)
        if existing is None:
            return OperationResult(self.path, Outcome.ALREADY_APPLIED)
        if existing == self.expected_content:
            workspace.delete(self.path)
            return OperationResult(self.path, Outcome.APPLIED)
        return OperationResult(self.path, Outcome.CONFLICT, "file was modified locally")


@dataclass(frozen=True, slots=True)
class ManualStep:
    """A change nf-core's own commands make better than a text patch."""

    path: str
    instruction: str

    def apply(self, workspace: Workspace) -> OperationResult:
        return OperationResult(self.path, Outcome.MANUAL, self.instruction)


@dataclass(frozen=True, slots=True)
class NfCoreComponent:
    """An nf-core module or subworkflow the template pins at `git_sha`.

    Pipelines update these with `nf-core modules update`, often past the
    template's version, so patching their files would conflict. Instead
    this compares modules.json and names the command to run. A `git_sha`
    of None means the template dropped the component.
    """

    kind: str
    name: str
    git_sha: str | None
    path: str = "modules.json"

    def apply(self, workspace: Workspace) -> OperationResult:
        installed_sha = self._installed_sha(workspace)
        command = f"nf-core {self.kind}"

        if self.git_sha is None:
            if installed_sha is None:
                return self._result(Outcome.ALREADY_APPLIED)
            return self._result(Outcome.MANUAL, f"template dropped it: `{command} remove {self.name}`")

        if installed_sha == self.git_sha:
            return self._result(Outcome.ALREADY_APPLIED)
        if installed_sha is None:
            message = f"not installed: `{command} install {self.name}` (template has {self.git_sha})"
            return self._result(Outcome.MANUAL, message)
        message = (
            f"pipeline has {installed_sha}, template {self.git_sha}: `{command} update {self.name}` if yours is older"
        )
        return self._result(Outcome.MANUAL, message)

    def _installed_sha(self, workspace: Workspace) -> str | None:
        content = workspace.read(self.path)
        if content is None:
            return None
        repos = json.loads(content).get("repos", {})
        components = repos.get(NF_CORE_MODULES_REMOTE, {}).get(self.kind, {}).get("nf-core", {})
        entry = components.get(self.name)
        if entry is None:
            return None
        return entry.get("git_sha")

    def _result(self, outcome: Outcome, message: str = "") -> OperationResult:
        return OperationResult(f"{self.kind}/nf-core/{self.name}", outcome, message)
