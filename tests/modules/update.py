import filecmp
import os
import shutil
import tempfile

import yaml

import nf_core.utils
from nf_core.modules.install import ModuleInstall
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME
from nf_core.modules.update import ModuleUpdate

from ..utils import (
    GITLAB_BRANCH_TEST_BRANCH,
    GITLAB_BRANCH_TEST_NEW_SHA,
    GITLAB_BRANCH_TEST_OLD_SHA,
    GITLAB_DEFAULT_BRANCH,
    GITLAB_REPO,
    GITLAB_URL,
    OLD_TRIMGALORE_SHA,
)


def test_install_and_update(self):
    """Installs a module in the pipeline and updates it (no change)"""
    self.mods_install.install("trimgalore")
    update_obj = ModuleUpdate(self.pipeline_dir, show_diff=False)

    # Copy the module files and check that they are unaffected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_tmpdir = os.path.join(tmpdir, "trimgalore")
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, trimgalore_tmpdir)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(trimgalore_tmpdir, trimgalore_path) is True


def test_install_at_hash_and_update(self):
    """Installs an old version of a module in the pipeline and updates it"""
    self.mods_install_old.install("trimgalore")
    update_obj = ModuleUpdate(self.pipeline_dir, show_diff=False)

    # Copy the module files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_tmpdir = os.path.join(tmpdir, "trimgalore")
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, trimgalore_tmpdir)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(trimgalore_tmpdir, trimgalore_path) is False

    # Check that the modules.json is correctly updated
    mod_json_obj = ModulesJson(self.pipeline_dir)
    mod_json = mod_json_obj.get_modules_json()
    # Get the up-to-date git_sha for the module from the ModulesRepo object
    correct_git_sha = update_obj.modules_repo.get_latest_module_version("trimgalore")
    current_git_sha = mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["trimgalore"]["git_sha"]
    assert correct_git_sha == current_git_sha


def test_install_at_hash_and_update_and_save_diff_to_file(self):
    """Installs an old version of a module in the pipeline and updates it"""
    self.mods_install_old.install("trimgalore")
    patch_path = os.path.join(self.pipeline_dir, "trimgalore.patch")
    update_obj = ModuleUpdate(self.pipeline_dir, save_diff_fn=patch_path)

    # Copy the module files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_tmpdir = os.path.join(tmpdir, "trimgalore")
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, trimgalore_tmpdir)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(trimgalore_tmpdir, trimgalore_path) is True

    # TODO: Apply the patch to the module


def test_update_all(self):
    """Updates all modules present in the pipeline"""
    update_obj = ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    # Get the current modules.json
    assert update_obj.update() is True

    # We must reload the modules.json to get the updated version
    mod_json_obj = ModulesJson(self.pipeline_dir)
    mod_json = mod_json_obj.get_modules_json()
    # Loop through all modules and check that they are updated (according to the modules.json file)
    for mod in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]:
        correct_git_sha = list(update_obj.modules_repo.get_module_git_log(mod, depth=1))[0]["git_sha"]
        current_git_sha = mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][mod]["git_sha"]
        assert correct_git_sha == current_git_sha


def test_update_with_config_fixed_version(self):
    """Try updating when there are entries in the .nf-core.yml"""
    # Install trimgalore at the latest version
    self.mods_install.install("trimgalore")

    # Fix the trimgalore version in the .nf-core.yml to an old version
    update_config = {"nf-core/modules": {"trimgalore": OLD_TRIMGALORE_SHA}}
    tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(os.path.join(self.pipeline_dir, ".nf-core.yml"), "w") as f:
        yaml.dump(tools_config, f)

    # Update all modules in the pipeline
    update_obj = ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # Check that the git sha for trimgalore is correctly downgraded
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    assert "trimgalore" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]
    assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["trimgalore"]
    assert mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["trimgalore"]["git_sha"] == OLD_TRIMGALORE_SHA


def test_update_with_config_dont_update(self):
    """Try updating when module is to be ignored"""
    # Install an old version of trimgalore
    self.mods_install_old.install("trimgalore")

    # Set the trimgalore field to no update in the .nf-core.yml
    update_config = {"nf-core/modules": {"trimgalore": False}}
    tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(os.path.join(self.pipeline_dir, ".nf-core.yml"), "w") as f:
        yaml.dump(tools_config, f)

    # Update all modules in the pipeline
    update_obj = ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # Check that the git sha for trimgalore is correctly downgraded
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    assert "trimgalore" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]
    assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["trimgalore"]
    assert mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["trimgalore"]["git_sha"] == OLD_TRIMGALORE_SHA


def test_update_with_config_fix_all(self):
    """Fix the version of all nf-core modules"""
    self.mods_install.install("trimgalore")

    # Fix the version of all nf-core modules in the .nf-core.yml to an old version
    update_config = {"nf-core/modules": OLD_TRIMGALORE_SHA}
    tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(os.path.join(self.pipeline_dir, ".nf-core.yml"), "w") as f:
        yaml.dump(tools_config, f)

    # Update all modules in the pipeline
    update_obj = ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # Check that the git sha for trimgalore is correctly downgraded
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    for module in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]:
        assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][module]
        assert mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][module]["git_sha"] == OLD_TRIMGALORE_SHA


def test_update_with_config_no_updates(self):
    """Don't update any nf-core modules"""
    self.mods_install_old.install("trimgalore")
    old_mod_json = ModulesJson(self.pipeline_dir).get_modules_json()

    # Fix the version of all nf-core modules in the .nf-core.yml to an old version
    update_config = {"nf-core/modules": False}
    tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(os.path.join(self.pipeline_dir, ".nf-core.yml"), "w") as f:
        yaml.dump(tools_config, f)

    # Update all modules in the pipeline
    update_obj = ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # Check that the git sha for trimgalore is correctly downgraded
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    for module in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]:
        assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][module]
        assert (
            mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][module]["git_sha"]
            == old_mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][module]["git_sha"]
        )


def test_update_different_branch_single_module(self):
    """Try updating a module in a specific branch"""
    install_obj = ModuleInstall(
        self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH, sha=GITLAB_BRANCH_TEST_OLD_SHA
    )
    install_obj.install("fastp")
    update_obj = ModuleUpdate(
        self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH, show_diff=False
    )
    update_obj.update("fastp")

    # Verify that the branch entry was updated correctly
    modules_json = ModulesJson(self.pipeline_dir)
    assert modules_json.get_module_branch("fastp", GITLAB_REPO) == GITLAB_BRANCH_TEST_BRANCH
    assert modules_json.get_module_version("fastp", GITLAB_REPO) == GITLAB_BRANCH_TEST_NEW_SHA


def test_update_different_branch_mixed_modules_main(self):
    """Try updating all modules where MultiQC is installed from main branch"""
    # Install fastp
    install_obj = ModuleInstall(
        self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH, sha=GITLAB_BRANCH_TEST_OLD_SHA
    )
    install_obj.install("fastp")

    # Install MultiQC from gitlab default branch
    install_obj = ModuleInstall(self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_DEFAULT_BRANCH)
    install_obj.install("multiqc")

    # Try updating
    update_obj = ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    modules_json = ModulesJson(self.pipeline_dir)
    # Verify that the branch entry was updated correctly
    assert modules_json.get_module_branch("fastp", GITLAB_REPO) == GITLAB_BRANCH_TEST_BRANCH
    assert modules_json.get_module_version("fastp", GITLAB_REPO) == GITLAB_BRANCH_TEST_NEW_SHA
    # MultiQC is present in both branches but should've been updated using the 'main' branch
    assert modules_json.get_module_branch("multiqc", GITLAB_REPO) == GITLAB_DEFAULT_BRANCH


def test_update_different_branch_mix_modules_branch_test(self):
    """Try updating all modules where MultiQC is installed from branch-test branch"""
    # Install multiqc from the branch-test branch
    install_obj = ModuleInstall(
        self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH, sha=GITLAB_BRANCH_TEST_OLD_SHA
    )
    install_obj.install("multiqc")
    update_obj = ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    update_obj.update()

    modules_json = ModulesJson(self.pipeline_dir)
    assert modules_json.get_module_branch("multiqc", GITLAB_REPO) == GITLAB_BRANCH_TEST_BRANCH
    assert modules_json.get_module_version("multiqc", GITLAB_REPO) == GITLAB_BRANCH_TEST_NEW_SHA


def cmp_module(dir1, dir2):
    """Compare two versions of the same module"""
    files = ["main.nf", "meta.yml"]
    return all(filecmp.cmp(os.path.join(dir1, f), os.path.join(dir2, f), shallow=False) for f in files)
