"""Tests for applying a template update to a pipeline branch as a merge commit"""

from pathlib import Path

import git
import pytest

from nf_core.pipelines.template_migrations.apply import merge_template

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
    """A pipeline whose dev merged the 3.3.1 template, with 3.3.2 now on TEMPLATE."""
    repo = git.Repo.init(tmp_path / "pipeline", initial_branch="TEMPLATE")
    with repo.config_writer() as config:
        config.set_value("user", "name", "t")
        config.set_value("user", "email", "t@example.com")

    commit_files(
        repo,
        {
            ".nf-core.yml": "nf_core_version: 3.3.1\n",
            "base.config": BASE_CONFIG,
            "README.md": "template readme\n",
            "ro-crate-metadata.json": '{"date": 1}\n',
        },
        "Template update for nf-core/tools version 3.3.1",
    )
    repo.git.switch("-q", "-c", "dev")
    commit_files(repo, {"README.md": "pipeline readme\n"}, "customise the README")
    repo.git.switch("-q", "TEMPLATE")
    commit_files(
        repo,
        {
            ".nf-core.yml": "nf_core_version: 3.3.2\n",
            "base.config": BASE_CONFIG.replace("retry = 104", "retry = 104 + 175"),
            "ro-crate-metadata.json": '{"date": 2}\n',
        },
        "Template update for nf-core/tools version 3.3.2",
    )
    repo.git.switch("-q", "dev")
    return repo


def show(repo: git.Repo, ref: str, path: str) -> str:
    return repo.git.show(f"{ref}:{path}", strip_newline_in_stdout=False)


def test_clean_update_becomes_a_merge_commit_of_base_and_template(repo: git.Repo) -> None:
    # Given
    dev_sha = repo.commit("dev").hexsha
    template_sha = repo.commit("TEMPLATE").hexsha

    # When
    result = merge_template(repo, "dev", "TEMPLATE")

    # Then
    assert result.report.succeeded
    assert result.commit is not None
    merge_commit = repo.commit(result.commit)
    assert [parent.hexsha for parent in merge_commit.parents] == [dev_sha, template_sha]
    assert show(repo, result.commit, "base.config") == BASE_CONFIG.replace("retry = 104", "retry = 104 + 175")
    assert show(repo, result.commit, "README.md") == "pipeline readme\n"
    assert show(repo, result.commit, ".nf-core.yml") == "nf_core_version: 3.3.2\n"


def test_merge_leaves_the_checkout_and_worktrees_untouched(repo: git.Repo) -> None:
    # Given
    status_before = repo.git.status("--porcelain")

    # When
    merge_template(repo, "dev", "TEMPLATE")

    # Then
    assert repo.git.status("--porcelain") == status_before
    assert repo.active_branch.name == "dev"
    assert len(repo.git.worktree("list").splitlines()) == 1


def test_update_starts_from_the_template_dev_last_merged(repo: git.Repo) -> None:
    # Given a 3.3.3 sync on top of the 3.3.2 one that dev never merged
    repo.git.switch("-q", "TEMPLATE")
    commit_files(repo, {".nf-core.yml": "nf_core_version: 3.3.3\n", "new.txt": "new\n"}, "3.3.3")
    repo.git.switch("-q", "dev")

    # When
    result = merge_template(repo, "dev", "TEMPLATE")

    # Then the 3.3.2 change is applied too
    assert result.report.from_version == "3.3.1"
    assert result.report.to_version == "3.3.3"
    assert result.commit is not None
    assert show(repo, result.commit, "base.config") == BASE_CONFIG.replace("retry = 104", "retry = 104 + 175")
    assert show(repo, result.commit, "new.txt") == "new\n"


def test_conflicting_update_creates_no_commit(repo: git.Repo) -> None:
    # Given
    commit_files(repo, {"base.config": BASE_CONFIG.replace("retry = 104", "retry = 'custom'")}, "customise retry")

    # When
    result = merge_template(repo, "dev", "TEMPLATE")

    # Then
    assert result.commit is None
    assert not result.report.succeeded
    markdown = result.report.render_markdown()
    assert "`base.config`: old text not found" in markdown
    assert "+retry = 104 + 175" in markdown


def test_allow_conflicts_commits_what_fits_and_holds_back_conflicting_files(repo: git.Repo) -> None:
    # Given a base.config edit that blocks one of its two template changes
    repo.git.switch("-q", "TEMPLATE")
    template_config = BASE_CONFIG.replace("retry = 104", "retry = 104 + 175").replace("memory = 1", "memory = 2")
    commit_files(
        repo,
        {".nf-core.yml": "nf_core_version: 3.3.3\n", "base.config": template_config, "new.txt": "n\n"},
        "3.3.3",
    )
    repo.git.switch("-q", "dev")
    customised_config = BASE_CONFIG.replace("memory = 1", "memory = 'custom'")
    commit_files(repo, {"base.config": customised_config}, "customise memory")

    # When
    result = merge_template(repo, "dev", "TEMPLATE", allow_conflicts=True)

    # Then
    assert result.commit is not None
    assert not result.report.succeeded
    assert show(repo, result.commit, "new.txt") == "n\n"
    assert show(repo, result.commit, "base.config") == customised_config
    held_back = [result for result in result.report.conflicts if "held back" in result.message]
    assert [result.path for result in held_back] == ["base.config"]


def test_report_lists_manual_steps_as_a_checklist(repo: git.Repo) -> None:
    # Given / When
    result = merge_template(repo, "dev", "TEMPLATE")
    markdown = result.report.render_markdown()

    # Then
    assert "- [ ] `ro-crate-metadata.json`: regenerate with `nf-core pipelines rocrate`" in markdown


def test_template_files_the_pipeline_ignores_are_still_merged(repo: git.Repo) -> None:
    # Given dev ignores a path the template adds a file under
    commit_files(repo, {".gitignore": "results/\n"}, "ignore results")
    repo.git.switch("-q", "TEMPLATE")
    commit_files(repo, {".nf-core.yml": "nf_core_version: 3.3.3\n", "results/README.md": "keep\n"}, "3.3.3")
    repo.git.switch("-q", "dev")

    # When
    result = merge_template(repo, "dev", "TEMPLATE")

    # Then
    assert result.commit is not None
    assert show(repo, result.commit, "results/README.md") == "keep\n"


def test_version_is_stamped_in_nf_core_yaml(tmp_path: Path) -> None:
    # Given a pipeline that uses the .nf-core.yaml spelling
    repo = git.Repo.init(tmp_path / "yaml-pipeline", initial_branch="TEMPLATE")
    with repo.config_writer() as config:
        config.set_value("user", "name", "t")
        config.set_value("user", "email", "t@example.com")
    commit_files(repo, {".nf-core.yaml": "nf_core_version: 4.0.3\n# keep me\n", "a.txt": "a\n"}, "4.0.3")
    repo.git.switch("-q", "-c", "dev")
    repo.git.switch("-q", "TEMPLATE")
    commit_files(repo, {".nf-core.yaml": "nf_core_version: 4.1.0\n# keep me\n", "a.txt": "b\n"}, "4.1.0")

    # When
    result = merge_template(repo, "dev", "TEMPLATE")

    # Then
    assert result.report.from_version == "4.0.3"
    assert result.report.to_version == "4.1.0"
    assert result.commit is not None
    assert show(repo, result.commit, ".nf-core.yaml") == "nf_core_version: 4.1.0\n# keep me\n"
