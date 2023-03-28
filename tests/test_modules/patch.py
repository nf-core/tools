import os
import tempfile
from pathlib import Path

import pytest

import nf_core.components.components_command
import nf_core.modules

from ..utils import GITLAB_URL

"""
Test the 'nf-core modules patch' command

Uses a branch (patch-tester) in the GitLab nf-core/modules-test repo when
testing if the update commands works correctly with patch files
"""

ORG_SHA = "775fcd090fb776a0be695044f8ab1af8896c8452"
CORRECT_SHA = "335cd32405568ca3b6d4c05ab1e8a98c21e18a4d"
SUCCEED_SHA = "f1566140c752e9c68fffc189fbe8cb9ee942b3ca"
FAIL_SHA = "1fc8b0f953d915d66ee40d28bc337ff0998d05bd"
BISMARK_ALIGN = "bismark/align"
REPO_NAME = "nf-core"
PATCH_BRANCH = "patch-tester"
REPO_URL = "https://gitlab.com/nf-core/modules-test.git"


def setup_patch(pipeline_dir, modify_module):
    install_obj = nf_core.modules.ModuleInstall(
        pipeline_dir, prompt=False, force=False, remote_url=GITLAB_URL, branch=PATCH_BRANCH, sha=ORG_SHA
    )

    # Install the module
    install_obj.install(BISMARK_ALIGN)

    if modify_module:
        # Modify the module
        module_path = Path(pipeline_dir, "modules", REPO_NAME, BISMARK_ALIGN)
        modify_main_nf(module_path / "main.nf")


def modify_main_nf(path):
    """Modify a file to test patch creation"""
    with open(path, "r") as fh:
        lines = fh.readlines()
    # We want a patch file that looks something like:
    # -    tuple val(meta), path(reads)
    # -    path index
    # +    tuple val(meta), path(reads), path(index)
    for line_index in range(len(lines)):
        if lines[line_index] == "    tuple val(meta), path(reads)\n":
            lines[line_index] = "    tuple val(meta), path(reads), path(index)\n"
        elif lines[line_index] == "    path index\n":
            to_pop = line_index
    lines.pop(to_pop)
    with open(path, "w") as fh:
        fh.writelines(lines)


def test_create_patch_no_change(self):
    """Test creating a patch when there is no change to the module"""
    setup_patch(self.pipeline_dir, False)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    with pytest.raises(UserWarning):
        patch_obj.patch(BISMARK_ALIGN)

    module_path = Path(self.pipeline_dir, "modules", REPO_NAME, BISMARK_ALIGN)

    # Check that no patch file has been added to the directory
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml"}

    # Check the 'modules.json' contains no patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, REPO_URL, REPO_NAME) is None


def test_create_patch_change(self):
    """Test creating a patch when there is a change to the module"""
    setup_patch(self.pipeline_dir, True)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(BISMARK_ALIGN)

    module_path = Path(self.pipeline_dir, "modules", REPO_NAME, BISMARK_ALIGN)

    patch_fn = f"{'-'.join(BISMARK_ALIGN.split('/'))}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, REPO_URL, REPO_NAME) == Path(
        "modules", REPO_NAME, BISMARK_ALIGN, patch_fn
    )

    # Check that the correct lines are in the patch file
    with open(module_path / patch_fn, "r") as fh:
        patch_lines = fh.readlines()
    module_relpath = module_path.relative_to(self.pipeline_dir)
    assert f"--- {module_relpath / 'main.nf'}\n" in patch_lines, module_relpath / "main.nf"
    assert f"+++ {module_relpath / 'main.nf'}\n" in patch_lines
    assert "-    tuple val(meta), path(reads)\n" in patch_lines
    assert "-    path index\n" in patch_lines
    assert "+    tuple val(meta), path(reads), path(index)\n" in patch_lines


def test_create_patch_try_apply_successful(self):
    """
    Test creating a patch file and applying it to a new version of the the files
    """
    setup_patch(self.pipeline_dir, True)
    module_relpath = Path("modules", REPO_NAME, BISMARK_ALIGN)
    module_path = Path(self.pipeline_dir, module_relpath)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(BISMARK_ALIGN)

    patch_fn = f"{'-'.join(BISMARK_ALIGN.split('/'))}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, REPO_URL, REPO_NAME) == Path(
        "modules", REPO_NAME, BISMARK_ALIGN, patch_fn
    )

    update_obj = nf_core.modules.ModuleUpdate(
        self.pipeline_dir, sha=SUCCEED_SHA, remote_url=GITLAB_URL, branch=PATCH_BRANCH
    )
    # Install the new files
    install_dir = Path(tempfile.mkdtemp())
    update_obj.install_component_files(BISMARK_ALIGN, SUCCEED_SHA, update_obj.modules_repo, install_dir)

    # Try applying the patch
    module_install_dir = install_dir / BISMARK_ALIGN
    patch_relpath = module_relpath / patch_fn
    assert update_obj.try_apply_patch(BISMARK_ALIGN, REPO_NAME, patch_relpath, module_path, module_install_dir) is True

    # Move the files from the temporary directory
    update_obj.move_files_from_tmp_dir(BISMARK_ALIGN, install_dir, REPO_NAME, SUCCEED_SHA)

    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, REPO_URL, REPO_NAME) == Path(
        "modules", REPO_NAME, BISMARK_ALIGN, patch_fn
    )

    # Check that the correct lines are in the patch file
    with open(module_path / patch_fn, "r") as fh:
        patch_lines = fh.readlines()
    module_relpath = module_path.relative_to(self.pipeline_dir)
    assert f"--- {module_relpath / 'main.nf'}\n" in patch_lines
    assert f"+++ {module_relpath / 'main.nf'}\n" in patch_lines
    assert "-    tuple val(meta), path(reads)\n" in patch_lines
    assert "-    path index\n" in patch_lines
    assert "+    tuple val(meta), path(reads), path(index)\n" in patch_lines

    # Check that 'main.nf' is updated correctly
    with open(module_path / "main.nf", "r") as fh:
        main_nf_lines = fh.readlines()
    # These lines should have been removed by the patch
    assert "    tuple val(meta), path(reads)\n" not in main_nf_lines
    assert "    path index\n" not in main_nf_lines
    # This line should have been added
    assert "    tuple val(meta), path(reads), path(index)\n" in main_nf_lines


def test_create_patch_try_apply_failed(self):
    """
    Test creating a patch file and applying it to a new version of the the files
    """
    setup_patch(self.pipeline_dir, True)
    module_relpath = Path("modules", REPO_NAME, BISMARK_ALIGN)
    module_path = Path(self.pipeline_dir, module_relpath)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(BISMARK_ALIGN)

    patch_fn = f"{'-'.join(BISMARK_ALIGN.split('/'))}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, REPO_URL, REPO_NAME) == Path(
        "modules", REPO_NAME, BISMARK_ALIGN, patch_fn
    )

    update_obj = nf_core.modules.ModuleUpdate(
        self.pipeline_dir, sha=FAIL_SHA, remote_url=GITLAB_URL, branch=PATCH_BRANCH
    )
    # Install the new files
    install_dir = Path(tempfile.mkdtemp())
    update_obj.install_component_files(BISMARK_ALIGN, FAIL_SHA, update_obj.modules_repo, install_dir)

    # Try applying the patch
    module_install_dir = install_dir / BISMARK_ALIGN
    patch_path = module_relpath / patch_fn
    assert update_obj.try_apply_patch(BISMARK_ALIGN, REPO_NAME, patch_path, module_path, module_install_dir) is False


def test_create_patch_update_success(self):
    """
    Test creating a patch file and the updating the module

    Should have the same effect as 'test_create_patch_try_apply_successful'
    but uses higher level api
    """
    setup_patch(self.pipeline_dir, True)
    module_path = Path(self.pipeline_dir, "modules", REPO_NAME, BISMARK_ALIGN)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(BISMARK_ALIGN)

    patch_fn = f"{'-'.join(BISMARK_ALIGN.split('/'))}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, GITLAB_URL, REPO_NAME) == Path(
        "modules", REPO_NAME, BISMARK_ALIGN, patch_fn
    )

    # Update the module
    update_obj = nf_core.modules.ModuleUpdate(
        self.pipeline_dir,
        sha=SUCCEED_SHA,
        show_diff=False,
        update_deps=True,
        remote_url=GITLAB_URL,
        branch=PATCH_BRANCH,
    )
    assert update_obj.update(BISMARK_ALIGN)

    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, GITLAB_URL, REPO_NAME) == Path(
        "modules", REPO_NAME, BISMARK_ALIGN, patch_fn
    ), modules_json_obj.get_patch_fn(BISMARK_ALIGN, GITLAB_URL, REPO_NAME)

    # Check that the correct lines are in the patch file
    with open(module_path / patch_fn, "r") as fh:
        patch_lines = fh.readlines()
    module_relpath = module_path.relative_to(self.pipeline_dir)
    assert f"--- {module_relpath / 'main.nf'}\n" in patch_lines
    assert f"+++ {module_relpath / 'main.nf'}\n" in patch_lines
    assert "-    tuple val(meta), path(reads)\n" in patch_lines
    assert "-    path index\n" in patch_lines
    assert "+    tuple val(meta), path(reads), path(index)\n" in patch_lines

    # Check that 'main.nf' is updated correctly
    with open(module_path / "main.nf", "r") as fh:
        main_nf_lines = fh.readlines()
    # These lines should have been removed by the patch
    assert "    tuple val(meta), path(reads)\n" not in main_nf_lines
    assert "    path index\n" not in main_nf_lines
    # This line should have been added
    assert "    tuple val(meta), path(reads), path(index)\n" in main_nf_lines


def test_create_patch_update_fail(self):
    """
    Test creating a patch file and updating a module when there is a diff conflict
    """
    setup_patch(self.pipeline_dir, True)
    module_path = Path(self.pipeline_dir, "modules", REPO_NAME, BISMARK_ALIGN)

    # Try creating a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(BISMARK_ALIGN)

    patch_fn = f"{'-'.join(BISMARK_ALIGN.split('/'))}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(module_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check the 'modules.json' contains a patch file for the module
    modules_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    assert modules_json_obj.get_patch_fn(BISMARK_ALIGN, REPO_URL, REPO_NAME) == Path(
        "modules", REPO_NAME, BISMARK_ALIGN, patch_fn
    )

    # Save the file contents for downstream comparison
    with open(module_path / patch_fn, "r") as fh:
        patch_contents = fh.read()

    update_obj = nf_core.modules.ModuleUpdate(
        self.pipeline_dir, sha=FAIL_SHA, show_diff=False, update_deps=True, remote_url=GITLAB_URL, branch=PATCH_BRANCH
    )
    update_obj.update(BISMARK_ALIGN)

    # Check that the installed files have not been affected by the attempted patch
    temp_dir = Path(tempfile.mkdtemp())
    nf_core.components.components_command.ComponentCommand(
        "modules", self.pipeline_dir, GITLAB_URL, PATCH_BRANCH
    ).install_component_files(BISMARK_ALIGN, FAIL_SHA, update_obj.modules_repo, temp_dir)

    temp_module_dir = temp_dir / BISMARK_ALIGN
    for file in os.listdir(temp_module_dir):
        assert file in os.listdir(module_path)
        with open(module_path / file, "r") as fh:
            installed = fh.read()
        with open(temp_module_dir / file, "r") as fh:
            shouldbe = fh.read()
        assert installed == shouldbe

    # Check that the patch file is unaffected
    with open(module_path / patch_fn, "r") as fh:
        new_patch_contents = fh.read()
    assert patch_contents == new_patch_contents
