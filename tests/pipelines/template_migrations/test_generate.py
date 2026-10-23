"""Tests for generating template migration operations from two template commits"""

import json
from pathlib import Path

import git
import pytest

from nf_core.pipelines.template_migrations.generate import diff_hunks, generate_operations, template_version
from nf_core.pipelines.template_migrations.operations import (
    CreateFile,
    DeleteFile,
    ManualStep,
    NfCoreComponent,
    Outcome,
    Replace,
    Workspace,
    find_line_aligned,
)

BASE_CONFIG_OLD = "".join(f"line {number}\n" for number in range(1, 21))
BASE_CONFIG_NEW = BASE_CONFIG_OLD.replace("line 3\n", "line three\n").replace("line 18\n", "line eighteen\n")


def commit_files(repo: git.Repo, files: dict[str, str | None]) -> str:
    root = Path(repo.working_dir)
    for relative_path, content in files.items():
        file_path = root / relative_path
        if content is None:
            file_path.unlink()
            continue
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    repo.git.add(all=True)
    repo.git.commit("-q", "-m", "template", "--author", "t <t@example.com>")
    return repo.head.commit.hexsha


@pytest.fixture
def template_repo(tmp_path: Path) -> git.Repo:
    repo = git.Repo.init(tmp_path / "template")
    with repo.config_writer() as config:
        config.set_value("user", "name", "t")
        config.set_value("user", "email", "t@example.com")
    return repo


def apply_all(operations: list, root: Path) -> list:
    workspace = Workspace(root)
    results = [operation.apply(workspace) for operation in operations]
    workspace.commit()
    return results


def test_template_diff_applies_to_a_customised_pipeline(template_repo: git.Repo, tmp_path: Path) -> None:
    # Given two template commits
    old_ref = commit_files(
        template_repo,
        {
            ".nf-core.yml": "nf_core_version: 4.0.3\n",
            "base.config": BASE_CONFIG_OLD,
            "removed.yml": "gone\n",
        },
    )
    new_ref = commit_files(
        template_repo,
        {
            ".nf-core.yml": "nf_core_version: 4.1.0\n",
            "base.config": BASE_CONFIG_NEW,
            "removed.yml": None,
            "added.yml": "new\n\n",
        },
    )
    # And a pipeline that customised the middle of base.config
    pipeline = tmp_path / "pipeline"
    pipeline.mkdir()
    (pipeline / "removed.yml").write_text("gone\n")
    (pipeline / "base.config").write_text(BASE_CONFIG_OLD.replace("line 10\n", "my line\n"))

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)
    results = apply_all(operations, pipeline)

    # Then
    assert all(result.outcome is Outcome.APPLIED for result in results)
    assert (pipeline / "base.config").read_text() == BASE_CONFIG_NEW.replace("line 10\n", "my line\n")
    assert (pipeline / "added.yml").read_text() == "new\n\n"
    assert not (pipeline / "removed.yml").exists()


def test_nf_core_version_line_is_left_to_the_version_stamp(template_repo: git.Repo) -> None:
    # Given
    old_ref = commit_files(template_repo, {".nf-core.yml": "nf_core_version: 4.0.3\nrepository_type: pipeline\n"})
    new_ref = commit_files(template_repo, {".nf-core.yml": "nf_core_version: 4.1.0\nrepository_type: pipeline\n"})

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)

    # Then
    assert operations == []


def test_nf_core_components_and_generated_files_become_reported_steps(template_repo: git.Repo) -> None:
    # Given a template update that bumps multiqc and its generated files
    def modules_json(sha: str) -> str:
        content = {
            "repos": {"https://github.com/nf-core/modules.git": {"modules": {"nf-core": {"multiqc": {"git_sha": sha}}}}}
        }
        return json.dumps(content) + "\n"

    old_ref = commit_files(
        template_repo,
        {
            ".nf-core.yml": "nf_core_version: 4.0.3\n",
            "modules.json": modules_json("old000"),
            "modules/nf-core/multiqc/main.nf": "process MULTIQC { v1 }\n",
            "conf/containers_docker_amd64.config": "v1\n",
            "ro-crate-metadata.json": '{"@id": "#random-1"}\n',
        },
    )
    new_ref = commit_files(
        template_repo,
        {
            ".nf-core.yml": "nf_core_version: 4.1.0\n",
            "modules.json": modules_json("new111"),
            "modules/nf-core/multiqc/main.nf": "process MULTIQC { v2 }\n",
            "conf/containers_docker_amd64.config": "v2\n",
            "ro-crate-metadata.json": '{"@id": "#random-2"}\n',
        },
    )

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)

    # Then
    assert not any(isinstance(operation, (Replace, CreateFile, DeleteFile)) for operation in operations)
    assert NfCoreComponent("modules", "multiqc", git_sha="new111") in operations
    instructions = [operation.instruction for operation in operations if isinstance(operation, ManualStep)]
    assert "regenerate with `nf-core pipelines containers create-configs`" in instructions
    assert "regenerate with `nf-core pipelines rocrate`" in instructions


def test_binary_files_become_manual_steps(template_repo: git.Repo) -> None:
    # Given
    old_ref = commit_files(template_repo, {".nf-core.yml": "nf_core_version: 4.0.3\n", "logo.png": "\x00old"})
    new_ref = commit_files(template_repo, {".nf-core.yml": "nf_core_version: 4.1.0\n", "logo.png": "\x00new"})

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)

    # Then
    assert operations == [ManualStep("logo.png", "binary file changed in the template; copy it by hand")]


# Context around template changes
def test_unique_replacement_needs_no_context() -> None:
    # Given a one-line change whose new text is unique in both versions
    old_text = "header\nbadge 4.0.2\nfooter\n"
    new_text = "header\nbadge 4.0.3\nfooter\n"

    # When
    hunks = diff_hunks(old_text, new_text)

    # Then
    assert hunks == [("badge 4.0.2\n", "badge 4.0.3\n")]


def test_insertion_keeps_context_to_detect_reapplication() -> None:
    # Given
    old_text = "first\nlast\n"
    new_text = "first\nadded\nlast\n"

    # When
    hunks = diff_hunks(old_text, new_text)

    # Then
    assert hunks == [("first\nlast\n", "first\nadded\nlast\n")]


def test_repeated_lines_get_enough_context_to_be_unique() -> None:
    # Given a change to one of two identical lines
    old_text = "a\nvalue\nb\nvalue\nc\n"
    new_text = "a\nvalue\nb\nchanged\nc\n"

    # When
    hunks = diff_hunks(old_text, new_text)

    # Then
    assert hunks == [("b\nvalue\nc\n", "b\nchanged\nc\n")]


def test_new_executable_template_files_stay_executable(template_repo: git.Repo) -> None:
    # Given a template update that adds an executable script
    old_ref = commit_files(template_repo, {".nf-core.yml": "nf_core_version: 4.0.3\n"})
    script = Path(template_repo.working_dir) / "setup.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    new_ref = commit_files(template_repo, {".nf-core.yml": "nf_core_version: 4.1.0\n"})

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)

    # Then
    assert operations == [CreateFile("setup.sh", content="#!/bin/sh\n", executable=True)]


def test_nf_core_yaml_spelling_is_treated_like_nf_core_yml(template_repo: git.Repo) -> None:
    # Given a pipeline that uses .nf-core.yaml
    old_ref = commit_files(template_repo, {".nf-core.yaml": "nf_core_version: 4.0.3\nrepository_type: pipeline\n"})
    new_ref = commit_files(template_repo, {".nf-core.yaml": "nf_core_version: 4.1.0\nrepository_type: pipeline\n"})

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)

    # Then the version line is left to the version stamp
    assert operations == []


@pytest.mark.parametrize(
    ("old_text", "new_text"),
    [
        # A change whose neighbours repeat elsewhere grows into the next change.
        ("b\nb\na\n", "c\nb\nc\n"),
        # The last change grows back into the previous one.
        ("b\na\nb\nb\na\nb\n", "b\na\nb\nb\nb\nb\n"),
        # Two changes whose context overlaps become one.
        ("a\nb\nb\na\na\na\nb\n", "a\nc\nc\na\na\nb\nb\n"),
        # A template file that was empty.
        ("", "x\n"),
    ],
)
def test_hunks_turn_the_old_text_into_the_new_text(old_text: str, new_text: str) -> None:
    # Given
    hunks = diff_hunks(old_text, new_text)

    # When each hunk is replaced in turn
    text = old_text
    for old, new in hunks:
        positions = find_line_aligned(text, old)
        assert len(positions) == 1
        text = text[: positions[0]] + new + text[positions[0] + len(old) :]

    # Then
    assert text == new_text


def test_template_without_nf_core_config_still_generates_operations(template_repo: git.Repo) -> None:
    # Given
    old_ref = commit_files(template_repo, {"a.txt": "a\n"})
    new_ref = commit_files(template_repo, {"a.txt": None, "b.txt": "b\n"})

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)

    # Then
    assert operations == [DeleteFile("a.txt", expected_content="a\n"), CreateFile("b.txt", content="b\n")]
    assert template_version(template_repo.commit(new_ref)) is None


def test_component_files_missing_from_modules_json_are_not_patched(template_repo: git.Repo) -> None:
    # Given a module directory that modules.json does not list
    old_ref = commit_files(template_repo, {".nf-core.yml": "nf_core_version: 4.0.3\n"})
    new_ref = commit_files(
        template_repo, {".nf-core.yml": "nf_core_version: 4.1.0\n", "modules/nf-core/fastp/main.nf": "process FASTP\n"}
    )

    # When
    operations = generate_operations(template_repo, old_ref, new_ref)

    # Then
    assert operations == [NfCoreComponent("modules", "fastp", git_sha=None)]
