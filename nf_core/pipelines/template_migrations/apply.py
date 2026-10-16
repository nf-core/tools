"""Apply a template update to a pipeline branch as a merge commit.

A template sync PR merges the new TEMPLATE commit into the pipeline branch,
and git's merge of the two conflicts wherever the pipeline diverged from
the template. Here the pipeline branch is updated with migration operations
in a temporary worktree instead, and the result is recorded as a merge
commit of that branch and the template commit. It keeps TEMPLATE in the
branch's history, so the next sync merges from the right base.
"""

import logging
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path

import git

from nf_core.pipelines.template_migrations.generate import generate_operations, template_version
from nf_core.pipelines.template_migrations.operations import OperationResult, Outcome, Workspace
from nf_core.pipelines.template_migrations.version import NF_CORE_CONFIG_PATHS, stamp_version

log = logging.getLogger(__name__)


@dataclass(slots=True)
class MigrationReport:
    from_version: str | None
    to_version: str | None
    results: list[OperationResult] = field(default_factory=list)

    @property
    def conflicts(self) -> list[OperationResult]:
        return [result for result in self.results if result.outcome is Outcome.CONFLICT]

    @property
    def manual_steps(self) -> list[OperationResult]:
        return [result for result in self.results if result.outcome is Outcome.MANUAL]

    @property
    def succeeded(self) -> bool:
        return not self.conflicts

    def summary(self) -> str:
        counts = dict.fromkeys(Outcome, 0)
        for result in self.results:
            counts[result.outcome] += 1
        return ", ".join(f"{count} {outcome.value}" for outcome, count in counts.items())

    def render_markdown(self) -> str:
        """The report for a PR description: conflicts, then manual steps."""
        lines = [f"Template changes {self.from_version} → {self.to_version}: {self.summary()}.", ""]
        if self.conflicts:
            lines.append("Changes that need a maintainer:")
            lines.append("")
            for result in self.conflicts:
                lines.append(f"- :x: `{result.path}`: {result.message}")
                if result.suggestion:
                    lines.append(_suggestion_block(result.suggestion))
            lines.append("")
        if self.manual_steps:
            lines.append("Steps to run with nf-core tools:")
            lines.append("")
            for result in self.manual_steps:
                lines.append(f"- [ ] `{result.path}`: {result.message}")
            lines.append("")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class TemplateMergeResult:
    report: MigrationReport
    # The merge commit, or None when a conflict kept it from being made.
    commit: str | None


def merge_template(repo: git.Repo, base: str, template: str, allow_conflicts: bool = False) -> TemplateMergeResult:
    """Update `base` with the template changes on `template`.

    The changes are those between the template `base` last merged and
    `template`. Returns the merge commit when every change applied; with a
    conflict no commit is made. With `allow_conflicts` the merge commit
    holds every change that fits, files with a conflicting change are left
    as they were, and the report lists what is left to do.
    """
    base_commit = repo.commit(base)
    template_commit = repo.commit(template)
    merge_bases = repo.merge_base(base_commit, template_commit)
    if not merge_bases:
        raise ValueError(f"{base} has never merged a commit from {template}")
    last_merged_template = merge_bases[0]

    report = MigrationReport(
        from_version=template_version(last_merged_template),
        to_version=template_version(template_commit),
    )
    operations = generate_operations(repo, last_merged_template.hexsha, template_commit.hexsha)

    with tempfile.TemporaryDirectory() as temporary_directory:
        worktree_path = Path(temporary_directory) / "base"
        repo.git.worktree("add", "--quiet", "--detach", str(worktree_path), base_commit.hexsha)
        try:
            workspace = Workspace(worktree_path)
            report.results = _apply_operations(operations, workspace, allow_conflicts)
            commit = None
            if report.succeeded or allow_conflicts:
                if report.to_version is not None:
                    _stamp_version(workspace, report.to_version)
                workspace.commit()
                commit = _commit_merge(git.Repo(worktree_path), base_commit, template_commit, report)
        finally:
            repo.git.worktree("remove", "--force", str(worktree_path))

    log.info(f"Template migration {report.from_version} → {report.to_version}: {report.summary()}")
    return TemplateMergeResult(report, commit)


def _apply_operations(operations: list, workspace: Workspace, allow_conflicts: bool) -> list[OperationResult]:
    checkpoint = workspace.snapshot()
    results = [operation.apply(workspace) for operation in operations]
    conflicts = [result for result in results if result.outcome is Outcome.CONFLICT]
    if not conflicts:
        return results
    if not allow_conflicts:
        workspace.restore(checkpoint)
        return results
    return _hold_back_conflicting_files(results, workspace)


def _hold_back_conflicting_files(results: list[OperationResult], workspace: Workspace) -> list[OperationResult]:
    """Leave every file with a conflict as it was before the update.

    A file that got some of the template's changes but not others can end
    up half converted and broken, so its changes are reported together for
    a maintainer instead.
    """
    conflicting_paths = {result.path for result in results if result.outcome is Outcome.CONFLICT}
    workspace.discard(conflicting_paths)

    held_back_results: list[OperationResult] = []
    for result in results:
        if result.path in conflicting_paths and result.outcome is Outcome.APPLIED:
            result = replace(
                result, outcome=Outcome.CONFLICT, message="held back: another change to this file conflicts"
            )
        held_back_results.append(result)
    return held_back_results


def _stamp_version(workspace: Workspace, version: str) -> None:
    """Record the template version in whichever config file the pipeline uses."""
    for config_path in NF_CORE_CONFIG_PATHS:
        config = workspace.read(config_path)
        if config is not None:
            workspace.write(config_path, stamp_version(config, version))
            return


def _commit_merge(
    worktree: git.Repo, base_commit: git.Commit, template_commit: git.Commit, report: MigrationReport
) -> str:
    # --force adds template files the pipeline's .gitignore matches, as a git
    # merge would; the fresh worktree holds no other ignored files.
    worktree.git.add(all=True, force=True)
    tree = worktree.git.write_tree()
    message = (
        f"Merge nf-core/tools {report.to_version} template as migrations\n\n"
        "Applied the template changes one by one instead of with a git merge.\n"
        f"{report.summary()}."
    )
    return worktree.git.commit_tree(tree, "-p", base_commit.hexsha, "-p", template_commit.hexsha, "-m", message)


def _suggestion_block(diff: str) -> str:
    """A collapsed diff of the template change a conflict could not place."""
    fence = "````" if "```" in diff else "```"
    body = diff if diff.endswith("\n") else diff + "\n"
    indented = "".join(f"  {line}" for line in body.splitlines(keepends=True))
    return f"\n  <details><summary>template change</summary>\n\n  {fence}diff\n{indented}  {fence}\n\n  </details>\n"
