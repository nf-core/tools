import filecmp
import os
import shutil
import tempfile

import pytest

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


def test_install_at_hash_and_dryrun_update(self):
    """Installs an old version of a module in the pipeline and updates it"""
    self.mods_install_old.install("trimgalore")
    update_obj = nf_core.modules.update.ModuleUpdate(self.pipeline_dir, show_diff=True)

    # Copy the module files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, tmpdir, dirs_exist_ok=True)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(tmpdir, trimgalore_path) is True


def test_install_at_hash_and_update_and_save_diff_to_file(self):
    """Installs an old version of a module in the pipeline and updates it"""
    self.mods_install_old.install("trimgalore")
    update_obj = nf_core.modules.update.ModuleUpdate(self.pipeline_dir, save_diff_fn="trimgalore.patch")

    # Copy the module files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    trimgalore_path = os.path.join(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "trimgalore")
    shutil.copytree(trimgalore_path, tmpdir, dirs_exist_ok=True)

    assert update_obj.update("trimgalore") is True
    assert cmp_module(tmpdir, trimgalore_path) is True


def cmp_module(dir1, dir2):
    """Compare two versions of the same module"""
    files = ["main.nf", "meta.yml"]
    return all(filecmp.cmp(os.path.join(dir1, f), os.path.join(dir2, f)) for f in files)
