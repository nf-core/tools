import filecmp
import os
import shutil
import tempfile

import pytest

import nf_core.modules.modules_json
import nf_core.modules.update
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME

from ..utils import with_temporary_folder


def test_install_and_update(self):
    """Installs a module in the pipeline and updates it (no change)"""
    self.mods_install.install("trimgalore")
    update_obj = nf_core.modules.update.ModuleUpdate(self.pipeline_dir, show_diff=False)

    # Copy the module files and check that they are unaffected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, tmpdir, dirs_exist_ok=True)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(tmpdir, trimgalore_path) is True


def test_install_at_hash_and_update(self):
    """Installs an old version of a module in the pipeline and updates it"""
    self.mods_install_old.install("trimgalore")
    update_obj = nf_core.modules.update.ModuleUpdate(self.pipeline_dir, show_diff=False)

    # Copy the module files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, tmpdir, dirs_exist_ok=True)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(tmpdir, trimgalore_path) is False

    # Check that the modules.json is correctly updated
    mod_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    mod_json = mod_json_obj.get_modules_json()
    # Get the up-to-date git_sha for the module from the ModulesRepo object
    correct_git_sha = list(update_obj.modules_repo.get_module_git_log("trimgalore", depth=1))[0]["git_sha"]
    current_git_sha = mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["trimgalore"]["git_sha"]
    print(correct_git_sha, current_git_sha)
    assert correct_git_sha == current_git_sha


def test_install_at_hash_and_update_and_save_diff_to_file(self):
    """Installs an old version of a module in the pipeline and updates it"""
    self.mods_install_old.install("trimgalore")
    patch_path = os.path.join(self.pipeline_dir, "trimgalore.patch")
    update_obj = nf_core.modules.update.ModuleUpdate(self.pipeline_dir, save_diff_fn=patch_path)

    # Copy the module files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, tmpdir, dirs_exist_ok=True)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(tmpdir, trimgalore_path) is True


def test_update_all(self):
    """Updates all modules present in the pipeline"""
    update_obj = nf_core.modules.update.ModuleUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    # Get the current modules.json
    assert update_obj.update() is True

    # We must reload the modules.json to get the updated version
    mod_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    mod_json = mod_json_obj.get_modules_json()
    # Loop through all modules and check that they are updated (according to the modules.json file)
    for mod in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]:
        correct_git_sha = list(update_obj.modules_repo.get_module_git_log(mod, depth=1))[0]["git_sha"]
        current_git_sha = mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][mod]["git_sha"]
        assert correct_git_sha == current_git_sha


def cmp_module(dir1, dir2):
    """Compare two versions of the same module"""
    files = ["main.nf", "meta.yml"]
    return all(filecmp.cmp(os.path.join(dir1, f), os.path.join(dir2, f), shallow=False) for f in files)
