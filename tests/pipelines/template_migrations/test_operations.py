"""Tests for the idempotent operations a template migration is made of"""

import json
from pathlib import Path

from nf_core.pipelines.template_migrations.operations import (
    CreateFile,
    DeleteFile,
    ManualStep,
    NfCoreComponent,
    Outcome,
    Replace,
    Workspace,
)

MODULES_REPO = "https://github.com/nf-core/modules.git"


def make_workspace(root: Path, files: dict[str, str]) -> Workspace:
    for relative_path, content in files.items():
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    return Workspace(root)


def write_modules_json(root: Path, modules: dict[str, str], subworkflows: dict[str, str]) -> None:
    def entries(shas: dict[str, str]) -> dict:
        return {name: {"git_sha": sha} for name, sha in shas.items()}

    content = {
        "repos": {
            MODULES_REPO: {
                "modules": {"nf-core": entries(modules)},
                "subworkflows": {"nf-core": entries(subworkflows)},
            }
        }
    }
    (root / "modules.json").write_text(json.dumps(content))


# Replace
def test_replace_applies_when_old_text_occurs_once(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.config": "x = 1\ny = 2\n"})
    operation = Replace("a.config", old="y = 2\n", new="y = 3\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.APPLIED
    assert workspace.read("a.config") == "x = 1\ny = 3\n"


def test_replace_is_already_applied_when_only_new_text_is_present(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.config": "y = 3\n"})
    operation = Replace("a.config", old="y = 2\n", new="y = 3\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.ALREADY_APPLIED
    assert workspace.changed_paths() == []


def test_replace_conflicts_when_neither_text_is_present(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.config": "y = 42\n"})
    operation = Replace("a.config", old="y = 2\n", new="y = 3\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.CONFLICT
    assert workspace.read("a.config") == "y = 42\n"


def test_replace_conflicts_when_old_text_is_ambiguous(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.config": "y = 2\ny = 2\n"})
    operation = Replace("a.config", old="y = 2\n", new="y = 3\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.CONFLICT
    assert "2 times" in result.message


def test_replace_only_matches_whole_lines(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.txt": "line 13\nline 3\n"})
    operation = Replace("a.txt", old="line 3\n", new="line three\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.APPLIED
    assert workspace.read("a.txt") == "line 13\nline three\n"


def test_replace_conflicts_when_file_is_missing(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {})
    operation = Replace("a.config", old="y = 2\n", new="y = 3\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.CONFLICT


# CreateFile
def test_create_file_writes_a_missing_file(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {})
    operation = CreateFile("tests/nextflow.config", content="params {}\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.APPLIED
    assert workspace.read("tests/nextflow.config") == "params {}\n"


def test_create_file_is_already_applied_for_identical_file(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.txt": "same\n"})
    operation = CreateFile("a.txt", content="same\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.ALREADY_APPLIED


def test_create_file_conflicts_with_a_different_existing_file(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.txt": "local\n"})
    operation = CreateFile("a.txt", content="template\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.CONFLICT
    assert workspace.read("a.txt") == "local\n"


# DeleteFile
def test_delete_file_removes_an_unmodified_file(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"old.yml": "template\n"})
    operation = DeleteFile("old.yml", expected_content="template\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.APPLIED
    assert workspace.read("old.yml") is None


def test_delete_file_conflicts_when_file_was_customised(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"old.yml": "customised\n"})
    operation = DeleteFile("old.yml", expected_content="template\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.CONFLICT
    assert workspace.read("old.yml") == "customised\n"


def test_delete_file_is_already_applied_when_file_is_gone(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {})
    operation = DeleteFile("old.yml", expected_content="template\n")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.ALREADY_APPLIED


# ManualStep
def test_manual_step_reports_its_instruction(tmp_path: Path) -> None:
    # Given
    workspace = Workspace(tmp_path)
    operation = ManualStep("ro-crate-metadata.json", "run `nf-core pipelines rocrate`")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.MANUAL
    assert result.message == "run `nf-core pipelines rocrate`"
    assert workspace.changed_paths() == []


# NfCoreComponent
def test_component_at_template_version_is_already_applied(tmp_path: Path) -> None:
    # Given
    write_modules_json(tmp_path, {"multiqc": "abc123"}, {})
    operation = NfCoreComponent("modules", "multiqc", git_sha="abc123")

    # When
    result = operation.apply(Workspace(tmp_path))

    # Then
    assert result.outcome is Outcome.ALREADY_APPLIED


def test_component_at_other_version_asks_for_an_update(tmp_path: Path) -> None:
    # Given
    write_modules_json(tmp_path, {"multiqc": "old000"}, {})
    operation = NfCoreComponent("modules", "multiqc", git_sha="abc123")

    # When
    result = operation.apply(Workspace(tmp_path))

    # Then
    assert result.outcome is Outcome.MANUAL
    assert "nf-core modules update multiqc" in result.message
    assert "old000" in result.message


def test_missing_component_asks_for_an_install(tmp_path: Path) -> None:
    # Given
    write_modules_json(tmp_path, {}, {})
    operation = NfCoreComponent("subworkflows", "utils_nfschema_plugin", git_sha="abc123")

    # When
    result = operation.apply(Workspace(tmp_path))

    # Then
    assert result.outcome is Outcome.MANUAL
    assert "nf-core subworkflows install utils_nfschema_plugin" in result.message


def test_component_dropped_by_template_asks_for_removal(tmp_path: Path) -> None:
    # Given
    write_modules_json(tmp_path, {}, {"utils_nfvalidation_plugin": "a1"})
    operation = NfCoreComponent("subworkflows", "utils_nfvalidation_plugin", git_sha=None)

    # When
    result = operation.apply(Workspace(tmp_path))

    # Then
    assert result.outcome is Outcome.MANUAL
    assert "nf-core subworkflows remove utils_nfvalidation_plugin" in result.message


def test_component_dropped_by_template_and_pipeline_is_already_applied(tmp_path: Path) -> None:
    # Given
    write_modules_json(tmp_path, {}, {})
    operation = NfCoreComponent("subworkflows", "utils_nfvalidation_plugin", git_sha=None)

    # When
    result = operation.apply(Workspace(tmp_path))

    # Then
    assert result.outcome is Outcome.ALREADY_APPLIED


# Workspace
def test_workspace_only_touches_disk_on_commit(tmp_path: Path) -> None:
    # Given
    workspace = make_workspace(tmp_path, {"a.txt": "before\n", "b.txt": "x"})
    workspace.write("a.txt", "after\n")
    workspace.delete("b.txt")
    workspace.write("new/c.txt", "c\n")

    # When
    content_before_commit = (tmp_path / "a.txt").read_text()
    workspace.commit()

    # Then
    assert content_before_commit == "before\n"
    assert (tmp_path / "a.txt").read_text() == "after\n"
    assert not (tmp_path / "b.txt").exists()
    assert (tmp_path / "new/c.txt").read_text() == "c\n"


def test_workspace_keeps_crlf_line_endings(tmp_path: Path) -> None:
    # Given a file with Windows line endings
    (tmp_path / "a.txt").write_bytes(b"x = 1\r\ny = 2\r\n")
    workspace = Workspace(tmp_path)
    operation = Replace("a.txt", old="y = 2\r\n", new="y = 3\r\n")

    # When
    result = operation.apply(workspace)
    workspace.commit()

    # Then
    assert result.outcome is Outcome.APPLIED
    assert (tmp_path / "a.txt").read_bytes() == b"x = 1\r\ny = 3\r\n"


def test_create_file_can_make_an_executable_file(tmp_path: Path) -> None:
    # Given
    workspace = Workspace(tmp_path)
    operation = CreateFile(".devcontainer/setup.sh", content="#!/bin/sh\n", executable=True)

    # When
    operation.apply(workspace)
    workspace.commit()

    # Then
    assert (tmp_path / ".devcontainer/setup.sh").stat().st_mode & 0o111


def test_component_without_modules_json_asks_for_an_install(tmp_path: Path) -> None:
    # Given a pipeline with no modules.json
    workspace = Workspace(tmp_path)
    operation = NfCoreComponent("modules", "multiqc", git_sha="abc123")

    # When
    result = operation.apply(workspace)

    # Then
    assert result.outcome is Outcome.MANUAL
    assert "nf-core modules install multiqc" in result.message
