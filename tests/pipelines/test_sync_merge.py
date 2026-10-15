"""Tests covering the merge conflict resolution of the sync command"""

from pathlib import Path

import git
import pytest

from nf_core.pipelines.sync_merge import apply_hunk, diff_hunks, merge_template

BASE = "a\nb\nc\nd\ne\nf\ng\n"


def test_diff_hunks_without_context_when_unique():
    assert diff_hunks(BASE, BASE.replace("b\n", "B\n")) == [("b\n", "B\n")]


def test_diff_hunks_grows_context_until_unique():
    old = "x\nfoo\ny\nfoo\nz\n"
    new = "x\nfoo\ny\nbar\nz\n"
    assert diff_hunks(old, new) == [("y\nfoo\nz\n", "y\nbar\nz\n")]


def test_diff_hunks_insertion_needs_context():
    assert diff_hunks(BASE, BASE.replace("b\n", "b\nnew\n")) == [("b\nc\n", "b\nnew\nc\n")]


def test_apply_hunk():
    assert apply_hunk("a\nb\nc\n", "b\n", "B\n") == "a\nB\nc\n"
    # Only whole lines match
    assert apply_hunk("ab\nc\n", "b\n", "B\n") is None
    # Already applied
    assert apply_hunk("a\nB\nc\n", "b\n", "B\n") == "a\nB\nc\n"
    # Ambiguous
    assert apply_hunk("b\nb\n", "b\n", "B\n") is None
    # Missing
    assert apply_hunk("a\nc\n", "b\n", "B\n") is None


@pytest.fixture
def repo(tmp_path: Path) -> git.Repo:
    repo = git.Repo.init(tmp_path, initial_branch="dev")
    with repo.config_writer() as config:
        config.set_value("user", "name", "nf-core-bot")
        config.set_value("user", "email", "core@nf-co.re")
    (tmp_path / "f.txt").write_text(BASE)
    (tmp_path / "other.txt").write_text("unchanged\n")
    repo.git.add(all=True)
    repo.index.commit("initial")
    return repo


def _commit(repo: git.Repo, branch: str, content: str) -> None:
    repo.git.checkout(branch)
    Path(repo.working_dir, "f.txt").write_text(content)
    repo.git.add(all=True)
    repo.index.commit(f"change on {branch}")


def _make_branches(repo: git.Repo, template: str, pipeline: str) -> None:
    repo.git.branch("TEMPLATE")
    _commit(repo, "TEMPLATE", template)
    _commit(repo, "dev", pipeline)


def test_merge_template_resolves_adjacent_edits(repo):
    _make_branches(repo, template=BASE.replace("b\n", "B\n"), pipeline=BASE.replace("c\n", "C\n"))

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template")

    assert result.resolved == ["f.txt"]
    assert result.unresolved == []
    assert result.commit is not None
    commit = repo.commit(result.commit)
    assert [parent.hexsha for parent in commit.parents] == [repo.commit("dev").hexsha, repo.commit("TEMPLATE").hexsha]
    assert commit.tree["f.txt"].data_stream.read().decode() == "a\nB\nC\nd\ne\nf\ng\n"
    # The repository itself is left untouched
    assert repo.active_branch.name == "dev"
    assert not repo.is_dirty(untracked_files=True)
    assert len(repo.git.worktree("list").splitlines()) == 1


def test_merge_template_resolves_already_applied_changes(repo):
    template = BASE.replace("b\n", "B\n").replace("f\n", "F\n")
    _make_branches(repo, template=template, pipeline=BASE.replace("b\n", "B\n").replace("c\n", "C\n"))

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template")

    assert result.commit is not None
    assert repo.commit(result.commit).tree["f.txt"].data_stream.read().decode() == "a\nB\nC\nd\ne\nF\ng\n"


def test_merge_template_leaves_real_conflicts(repo):
    _make_branches(repo, template=BASE.replace("b\n", "B\n"), pipeline=BASE.replace("b\n", "X\n"))

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template")

    assert result.commit is None
    assert result.unresolved == ["f.txt"]
    assert not repo.is_dirty(untracked_files=True)
    assert len(repo.git.worktree("list").splitlines()) == 1


def test_merge_template_clean_merge_needs_no_commit(repo):
    _make_branches(repo, template=BASE.replace("b\n", "B\n"), pipeline=BASE.replace("f\n", "F\n"))

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template")

    assert result.commit is None
    assert result.resolved == result.unresolved == []
