import json
import os
import tempfile
from pathlib import Path

import pytest

import nf_core.modules
import nf_core.modules.modules_command

from ..utils import GITLAB_URL

"""
Test the 'nf-core modules patch' command

Uses a branch (patch-tester) in the GitLab nf-core/modules-test repo when
testing if the update commands works correctly with patch files
"""

ORG_SHA = "22c7c12dc21e2f633c00862c1291ceda0a3b7066"
MODULE = "bismark/align"
REPO_NAME = "nf-core/modules-test"
PATCH_BRANCH = "patch-tester"


def setup_patch(pipeline_dir, modify_module):
    install_obj = nf_core.modules.ModuleInstall(
        pipeline_dir, prompt=False, force=True, remote_url=GITLAB_URL, branch=PATCH_BRANCH, sha=ORG_SHA
    )

    # Install the module
    install_obj.install(MODULE)

    if modify_module:
        # Modify the module
        module_path = Path(pipeline_dir, "modules", REPO_NAME, MODULE)
        modify_main_nf(module_path / "main.nf")


def modify_main_nf(path):
    """Modify a file to test patch creation"""
    with open(path, "r") as fh:
        lines = fh.readlines()
    # We want a patch file that looks something like:
    # -    tuple val(meta), path(reads)
    # -    path index
    # +    tuple val(meta), path(reads), path(index)
    lines[10] = "    tuple val(meta), path(reads), path(index)\n"
    lines.pop(11)
    with open(path, "w") as fh:
        fh.writelines(lines)


def test_create_patch_no_change(self):
    """Test creating a patch when there is no change to the module"""
    setup_patch(self.pipeline_dir, False)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    with pytest.raises(UserWarning):
        patch_obj.patch(MODULE)

    module_path = Path(self.pipeline_dir, "modules", REPO_NAME, MODULE)

    # Check that no patch file has been added to the directory
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml"}

    # Check the 'modules.json' contains no patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(MODULE, REPO_NAME) is None


def test_create_patch_change(self):
    """Test creating a patch when there is a change to the module"""
    setup_patch(self.pipeline_dir, True)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(MODULE)

    module_path = Path(self.pipeline_dir, "modules", REPO_NAME, MODULE)

    patch_fn = f"{'-'.join(MODULE.split('/'))}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(MODULE, REPO_NAME) == Path("modules", REPO_NAME, MODULE, patch_fn)

    # Check that the correct lines are in the patch file
    with open(module_path / patch_fn, "r") as fh:
        patch_lines = fh.readlines()
    module_relpath = module_path.relative_to(self.pipeline_dir)
    assert f"--- {module_relpath / 'main.nf'}\n" in patch_lines, module_relpath / "main.nf"
    assert f"+++ {module_relpath / 'main.nf'}\n" in patch_lines
    assert "-    tuple val(meta), path(reads)\n" in patch_lines
    assert "-    path index\n" in patch_lines
    assert "+    tuple val(meta), path(reads), path(index)\n" in patch_lines
