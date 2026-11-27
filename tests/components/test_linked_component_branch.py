"""Unit tests for branch selection on linked components across remotes."""

from pathlib import Path
from unittest import mock

import pytest

from nf_core.components.constants import NF_CORE_MODULES_REMOTE
from nf_core.components.install import ComponentInstall
from nf_core.components.update import ComponentUpdate

FORK_REMOTE = "https://github.com/organization/nf-core-modules.git"
FEATURE_BRANCH = "feature/my-workflow"


def _make_updater(
    tmp_path: Path, component_type: str = "subworkflows", branch: str = FEATURE_BRANCH
) -> ComponentUpdate:
    updater = object.__new__(ComponentUpdate)
    updater.directory = tmp_path
    updater.component_type = component_type
    updater.branch = branch
    updater.current_remote = mock.MagicMock(remote_url=FORK_REMOTE, repo_path="my-organization")
    updater.modules_repo = updater.current_remote
    updater.modules_json = mock.MagicMock()
    return updater


def _make_installer(tmp_path: Path, component_type: str = "modules", branch: str = FEATURE_BRANCH) -> ComponentInstall:
    installer = object.__new__(ComponentInstall)
    installer.directory = tmp_path
    installer.component_type = component_type
    installer.branch = branch
    installer.sha = None
    installer.current_sha = None
    installer.current_remote = mock.MagicMock(remote_url=FORK_REMOTE, repo_path="my-organization")
    installer.modules_repo = installer.current_remote
    installer.repo_type = "modules"
    return installer


def test_get_components_to_update_preserves_upstream_branch_for_subworkflow(tmp_path: Path) -> None:
    updater = _make_updater(tmp_path, component_type="subworkflows")
    updater.modules_json.get_installed_by_entries.return_value = ["subworkflows"]
    updater.modules_json.get_modules_json.return_value = {
        "repos": {
            FORK_REMOTE: {
                "subworkflows": {
                    "my-organization": {
                        "my_subworkflow": {"branch": FEATURE_BRANCH, "installed_by": ["subworkflows"]},
                    }
                },
                "modules": {
                    "my-organization": {
                        "mymodule/command1": {"branch": FEATURE_BRANCH, "installed_by": ["my_subworkflow"]},
                    }
                },
            },
            NF_CORE_MODULES_REMOTE: {
                "modules": {
                    "nf-core": {
                        "fastqc": {"branch": "master", "installed_by": ["my_subworkflow"]},
                    }
                }
            },
        }
    }

    modules_to_update, subworkflows_to_update = updater.get_components_to_update("my_subworkflow")

    assert subworkflows_to_update == []
    by_name = {m["name"]: m for m in modules_to_update}
    assert by_name["fastqc"]["git_remote"] == NF_CORE_MODULES_REMOTE
    assert by_name["fastqc"].get("branch") == "master"
    assert by_name["mymodule/command1"]["git_remote"] == FORK_REMOTE
    assert "branch" not in by_name["mymodule/command1"]


def test_get_components_to_update_preserves_other_remote_branch_for_module(tmp_path: Path) -> None:
    updater = _make_updater(tmp_path, component_type="modules")
    updater.modules_json.get_installed_by_entries.return_value = ["upstream_sw"]
    updater.modules_json.get_modules_json.return_value = {
        "repos": {
            NF_CORE_MODULES_REMOTE: {
                "subworkflows": {
                    "nf-core": {
                        "upstream_sw": {"branch": "master", "installed_by": ["subworkflows"]},
                    }
                }
            }
        }
    }

    _, subworkflows_to_update = updater.get_components_to_update("mymodule/command1")

    assert subworkflows_to_update == [{"name": "upstream_sw", "git_remote": NF_CORE_MODULES_REMOTE, "branch": "master"}]


@pytest.mark.parametrize(
    ("component_dict", "expected_remote", "expected_branch"),
    [
        ({"name": "fastqc", "git_remote": NF_CORE_MODULES_REMOTE}, NF_CORE_MODULES_REMOTE, None),
        (
            {"name": "fastqc", "git_remote": NF_CORE_MODULES_REMOTE, "branch": "master"},
            NF_CORE_MODULES_REMOTE,
            "master",
        ),
        ({"name": "mymodule/command1", "git_remote": FORK_REMOTE}, FORK_REMOTE, FEATURE_BRANCH),
    ],
)
def test_update_dict_component_branch_selection(
    tmp_path: Path, component_dict: dict[str, str], expected_remote: str, expected_branch: str | None
) -> None:
    updater = _make_updater(tmp_path, component_type="modules")
    updater.update_all = False

    class _StopAfterInitError(Exception):
        pass

    with (
        mock.patch("nf_core.components.update.ModulesRepo") as mock_repo,
        mock.patch("nf_core.utils.load_tools_config", side_effect=_StopAfterInitError),
        pytest.raises(_StopAfterInitError),
    ):
        updater.update(component_dict, silent=True)

    mock_repo.assert_called_once_with(expected_remote, expected_branch)


@pytest.mark.parametrize(
    ("component_dict", "expected_remote", "expected_branch"),
    [
        ({"name": "fastqc", "git_remote": NF_CORE_MODULES_REMOTE}, NF_CORE_MODULES_REMOTE, None),
        (
            {"name": "fastqc", "git_remote": NF_CORE_MODULES_REMOTE, "branch": "master"},
            NF_CORE_MODULES_REMOTE,
            "master",
        ),
        ({"name": "mymodule/command1", "git_remote": FORK_REMOTE}, FORK_REMOTE, FEATURE_BRANCH),
    ],
)
def test_install_dict_component_branch_selection(
    tmp_path: Path, component_dict: dict[str, str], expected_remote: str, expected_branch: str | None
) -> None:
    installer = _make_installer(tmp_path, component_type="modules")

    with mock.patch("nf_core.components.install.ModulesRepo") as mock_repo:
        mock_repo.return_value.remote_url = expected_remote
        result = installer.install(component_dict, silent=True)

    assert result is False
    mock_repo.assert_called_once_with(expected_remote, expected_branch)


def test_manage_changes_in_linked_components_only_applies_branch_to_same_remote(tmp_path: Path) -> None:
    updater = _make_updater(tmp_path, component_type="subworkflows")
    included_modules = [
        {"name": "fastqc", "git_remote": NF_CORE_MODULES_REMOTE},
        {"name": "mymodule/command1"},
    ]

    with (
        mock.patch("nf_core.components.update.get_components_to_install", return_value=(included_modules, [])),
        mock.patch("nf_core.components.update.ComponentInstall") as mock_install_cls,
    ):
        updater.manage_changes_in_linked_components("my_subworkflow", [], [])

    installed_args = [call.args[0] for call in mock_install_cls.return_value.install.call_args_list]
    by_name = {m["name"]: m for m in installed_args}
    assert by_name["fastqc"]["git_remote"] == NF_CORE_MODULES_REMOTE
    assert by_name["fastqc"]["branch"] is None
    assert by_name["mymodule/command1"]["git_remote"] == FORK_REMOTE
    assert by_name["mymodule/command1"]["branch"] == FEATURE_BRANCH
