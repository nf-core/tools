"""Tests for applying template migrations as part of `nf-core pipelines sync`"""

from pathlib import Path
from unittest import mock

import git
import pytest

import nf_core.pipelines.sync
from nf_core.pipelines.sync import PipelineSync

BASE_CONFIG = "retry = 104\nfiller 1\nfiller 2\nmemory = 1\n"


def commit_files(repo: git.Repo, files: dict[str, str], message: str) -> str:
    root = Path(repo.working_dir)
    for relative_path, content in files.items():
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    repo.git.add(all=True)
    repo.git.commit("-q", "-m", message)
    return repo.head.commit.hexsha


@pytest.fixture
def repo(tmp_path: Path) -> git.Repo:
    """A pipeline mid-sync: TEMPLATE has a new commit and is checked out."""
    repo = git.Repo.init(tmp_path / "pipeline", initial_branch="TEMPLATE")
    with repo.config_writer() as config:
        config.set_value("user", "name", "t")
        config.set_value("user", "email", "t@example.com")

    commit_files(repo, {".nf-core.yml": "nf_core_version: 4.0.3\n", "base.config": BASE_CONFIG}, "template 4.0.3")
    repo.git.switch("-q", "-c", "dev")
    commit_files(repo, {"README.md": "pipeline readme\n"}, "pipeline work")
    repo.git.switch("-q", "TEMPLATE")
    commit_files(
        repo,
        {".nf-core.yml": "nf_core_version: 4.1.0\n", "base.config": BASE_CONFIG.replace("memory = 1", "memory = 2")},
        "Template update for nf-core/tools version 4.1.0",
    )
    return repo


def make_sync(repo: git.Repo, template_migrations: str) -> PipelineSync:
    """A PipelineSync at the point where the merge branch has just been created."""
    sync = PipelineSync.__new__(PipelineSync)
    sync.repo = repo
    sync.from_branch = "dev"
    sync.merge_branch = "nf-core-template-merge-4.1.0"
    sync.template_migrations = template_migrations
    sync.migration_result = None
    repo.create_head(sync.merge_branch)
    return sync


def test_clean_migration_moves_the_merge_branch_to_a_merge_with_dev(repo: git.Repo) -> None:
    # Given
    sync = make_sync(repo, "clean")
    dev_sha = repo.commit("dev").hexsha
    template_sha = repo.commit("TEMPLATE").hexsha

    # When
    sync.apply_template_migrations()

    # Then
    merge_commit = repo.commit(sync.merge_branch)
    assert [parent.hexsha for parent in merge_commit.parents] == [dev_sha, template_sha]
    assert repo.git.show(f"{sync.merge_branch}:README.md") == "pipeline readme"
    assert "memory = 2" in repo.git.show(f"{sync.merge_branch}:base.config")
    assert repo.active_branch.name == "TEMPLATE"


def test_conflicting_migration_leaves_the_plain_template_branch(repo: git.Repo) -> None:
    # Given dev customised the line the template changes
    repo.git.switch("-q", "dev")
    commit_files(repo, {"base.config": BASE_CONFIG.replace("memory = 1", "memory = 'custom'")}, "customise")
    repo.git.switch("-q", "TEMPLATE")
    sync = make_sync(repo, "clean")

    # When
    sync.apply_template_migrations()

    # Then
    assert repo.commit(sync.merge_branch).hexsha == repo.commit("TEMPLATE").hexsha
    assert sync.migration_result is not None
    assert sync.migration_result.commit is None


def test_partial_migration_pushes_what_fits(repo: git.Repo) -> None:
    # Given a conflict in base.config and a new file that fits
    repo.git.switch("-q", "dev")
    commit_files(repo, {"base.config": BASE_CONFIG.replace("memory = 1", "memory = 'custom'")}, "customise")
    repo.git.switch("-q", "TEMPLATE")
    commit_files(repo, {".nf-core.yml": "nf_core_version: 4.1.0\n", "new.txt": "new\n"}, "add a file")
    sync = make_sync(repo, "partial")

    # When
    sync.apply_template_migrations()

    # Then
    assert repo.git.show(f"{sync.merge_branch}:new.txt") == "new"
    assert "memory = 'custom'" in repo.git.show(f"{sync.merge_branch}:base.config")


def test_migrations_are_off_by_default(repo: git.Repo) -> None:
    # Given
    sync = make_sync(repo, "off")

    # When
    sync.apply_template_migrations()

    # Then
    assert repo.commit(sync.merge_branch).hexsha == repo.commit("TEMPLATE").hexsha
    assert sync.migration_result is None


def test_pull_request_body_includes_the_migration_report(repo: git.Repo) -> None:
    # Given
    sync = make_sync(repo, "clean")
    sync.apply_template_migrations()
    sync.gh_repo = "nf-core/testpipeline"
    sync.blog_post = ""
    sync.gh_api = mock.MagicMock()
    sync.gh_api.request_retry.return_value.json.return_value = {"html_url": "pr_url"}

    # When
    sync.make_pull_request()

    # Then
    body = sync.gh_api.request_retry.call_args.kwargs["post_data"]["body"]
    assert "already merges `dev`" in body
    assert "Template changes 4.0.3 → 4.1.0" in body


def test_long_reports_are_cut_to_fit_a_pull_request(repo: git.Repo) -> None:
    # Given
    sync = make_sync(repo, "clean")
    sync.apply_template_migrations()
    assert sync.migration_result is not None
    long_report = "x" * (nf_core.pipelines.sync.MAX_MIGRATION_REPORT_LENGTH + 100)

    # When
    with mock.patch.object(type(sync.migration_result.report), "render_markdown", return_value=long_report):
        section = sync._migration_pr_section()

    # Then
    assert len(section) < nf_core.pipelines.sync.MAX_MIGRATION_REPORT_LENGTH + 1000
    assert "report was cut" in section
    assert "sync log" not in section


def test_unexpected_migration_errors_fall_back_to_the_plain_merge(repo: git.Repo) -> None:
    # Given
    sync = make_sync(repo, "clean")

    # When
    with mock.patch.object(nf_core.pipelines.sync, "merge_template", side_effect=OSError("disk full")):
        sync.apply_template_migrations()

    # Then
    assert repo.commit(sync.merge_branch).hexsha == repo.commit("TEMPLATE").hexsha
    assert sync.migration_result is None


def test_long_reports_are_cut_between_entries(repo: git.Repo) -> None:
    # Given a report whose entries hold collapsed diffs
    sync = make_sync(repo, "clean")
    sync.apply_template_migrations()
    assert sync.migration_result is not None
    entry = (
        "- :x: `a.txt`: old text not found\n\n  <details>\n\n  ```diff\n  " + "x" * 1000 + "\n  ```\n\n  </details>\n"
    )
    long_report = "summary\n\n" + entry * (nf_core.pipelines.sync.MAX_MIGRATION_REPORT_LENGTH // len(entry) + 5)

    # When
    with mock.patch.object(type(sync.migration_result.report), "render_markdown", return_value=long_report):
        section = sync._migration_pr_section()

    # Then no collapsed diff is left open
    assert section.count("<details>") == section.count("</details>")
    assert section.count("```") % 2 == 0
