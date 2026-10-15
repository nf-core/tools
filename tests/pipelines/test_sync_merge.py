"""Tests covering the merge conflict resolution of the sync command"""

import json
from pathlib import Path

import git
import pytest

import nf_core.pipelines.sync_merge
from nf_core.components.constants import NF_CORE_MODULES_REMOTE
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


def _commit_files(repo: git.Repo, branch: str, files: dict[str, str | bytes], message: str = "change") -> None:
    if repo.head.is_valid():
        repo.git.checkout(branch)
    for name, content in files.items():
        path = Path(repo.working_dir, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
    repo.git.add(all=True)
    repo.index.commit(message)


def _modules_json(sha: str) -> str:
    return json.dumps(
        {
            "repos": {
                NF_CORE_MODULES_REMOTE: {
                    "modules": {"nf-core": {"fastqc": {"branch": "master", "git_sha": sha}}},
                }
            }
        },
        indent=4,
    )


def test_merge_template_keeps_pipeline_version_of_generated_files(repo):
    logo = "docs/images/nf-core-testpipeline_logo_light.png"
    _commit_files(repo, "dev", {"ro-crate-metadata.json": "{}\n", logo: b"\x89PNG old"})
    repo.git.branch("TEMPLATE")
    _commit_files(repo, "TEMPLATE", {"ro-crate-metadata.json": '{"template": 1}\n', logo: b"\x89PNG template"})
    _commit_files(repo, "dev", {"ro-crate-metadata.json": '{"pipeline": 1}\n', logo: b"\x89PNG pipeline"})

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template", regenerate=False)

    assert result.commit is not None
    assert set(result.by_rule) == {"ro-crate-metadata.json", logo}
    tree = repo.commit(result.commit).tree
    assert tree["ro-crate-metadata.json"].data_stream.read() == b'{"pipeline": 1}\n'
    assert tree[logo].data_stream.read() == b"\x89PNG pipeline"


def test_merge_template_restores_pipeline_components(repo, monkeypatch):
    module = "modules/nf-core/fastqc/main.nf"
    _commit_files(repo, "dev", {"modules.json": _modules_json("aaa"), module: "process FASTQC {\n  v1\n}\n"})
    repo.git.branch("TEMPLATE")
    _commit_files(repo, "TEMPLATE", {"modules.json": _modules_json("ccc"), module: "process FASTQC {\n  v3\n}\n"})
    _commit_files(repo, "dev", {"modules.json": _modules_json("bbb"), module: "process FASTQC {\n  v2\n}\n"})
    to_update = []

    def fake_update(worktree, components, result):
        to_update.extend(components)
        return False

    monkeypatch.setattr(nf_core.pipelines.sync_merge, "_update_components", fake_update)

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template")

    assert result.commit is not None
    assert "modules.json" in result.by_rule
    assert [(c.name, c.sha) for c in to_update] == [("fastqc", "ccc")]
    tree = repo.commit(result.commit).tree
    assert (
        json.loads(tree["modules.json"].data_stream.read())["repos"][NF_CORE_MODULES_REMOTE]["modules"]["nf-core"][
            "fastqc"
        ]["git_sha"]
        == "bbb"
    )
    assert tree[module].data_stream.read() == b"process FASTQC {\n  v2\n}\n"


def test_merge_template_uses_stamped_template_version_as_base(tmp_path):
    repo = git.Repo.init(tmp_path, initial_branch="dev")
    with repo.config_writer() as config:
        config.set_value("user", "name", "nf-core-bot")
        config.set_value("user", "email", "core@nf-co.re")
    subject = "Template update for nf-core/tools version {}"
    _commit_files(repo, "dev", {"f.txt": BASE, ".nf-core.yml": "nf_core_version: 1.0.0\n"}, subject.format("1.0.0"))
    repo.git.branch("TEMPLATE")
    template_2 = BASE.replace("b\n", "B\n")
    _commit_files(
        repo, "TEMPLATE", {"f.txt": template_2, ".nf-core.yml": "nf_core_version: 2.0.0\n"}, subject.format("2.0.0")
    )
    # Template 2.0.0 squash-merged into dev, plus a pipeline change
    _commit_files(
        repo, "dev", {"f.txt": template_2.replace("c\n", "C\n"), ".nf-core.yml": "nf_core_version: 2.0.0\n"}, "Squash"
    )
    _commit_files(
        repo,
        "TEMPLATE",
        {"f.txt": template_2.replace("d\n", "D\n"), ".nf-core.yml": "nf_core_version: 3.0.0\n"},
        subject.format("3.0.0"),
    )

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template", regenerate=False)

    assert result.commit is not None
    assert "TEMPLATE 2.0.0 commit as its base" in result.warnings[0]
    tree = repo.commit(result.commit).tree
    assert tree["f.txt"].data_stream.read().decode() == "a\nB\nC\nD\ne\nf\ng\n"
    assert tree[".nf-core.yml"].data_stream.read().decode() == "nf_core_version: 3.0.0\n"


def test_merge_template_discards_resolution_with_new_lint_errors(repo, monkeypatch):
    _commit_files(repo, "dev", {"main.nf": BASE})
    repo.git.branch("TEMPLATE")
    _commit_files(repo, "TEMPLATE", {"main.nf": BASE.replace("b\n", "B\n")})
    _commit_files(repo, "dev", {"main.nf": BASE.replace("c\n", "C\n")})
    lint_results = iter([{("main.nf", "Unexpected input")}, set()])
    monkeypatch.setattr(nf_core.pipelines.sync_merge, "_lint_errors", lambda worktree, files: next(lint_results))

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template", regenerate=False)

    assert result.commit is None
    assert result.unresolved == ["main.nf"]
    assert result.conflicts == ["main.nf"]
    assert len(repo.git.worktree("list").splitlines()) == 1


def test_merge_template_keeps_pipeline_changelog_and_config(repo):
    _commit_files(
        repo,
        "dev",
        {"CHANGELOG.md": "# v1.0dev\n", ".nf-core.yml": "nf_core_version: 1.0.0\nrepository_type: pipeline\n"},
    )
    repo.git.branch("TEMPLATE")
    _commit_files(
        repo,
        "TEMPLATE",
        {"CHANGELOG.md": "# v1.0dev - [date]\n", ".nf-core.yml": "nf_core_version: 2.0.0\nrepository_type: pipeline\n"},
    )
    _commit_files(
        repo,
        "dev",
        {
            "CHANGELOG.md": "# v1.1\n\n- fix\n",
            ".nf-core.yml": "nf_core_version: 1.5.0\nrepository_type: pipeline\nlint: {}\n",
        },
    )

    result = merge_template(repo, "dev", "TEMPLATE", "Merge template", regenerate=False)

    assert result.commit is not None
    tree = repo.commit(result.commit).tree
    assert tree["CHANGELOG.md"].data_stream.read() == b"# v1.1\n\n- fix\n"
    assert tree[".nf-core.yml"].data_stream.read() == b"nf_core_version: 2.0.0\nrepository_type: pipeline\nlint: {}\n"
