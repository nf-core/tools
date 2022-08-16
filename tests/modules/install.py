import os

import pytest

from nf_core.modules.install import ModuleInstall
from nf_core.modules.modules_json import ModulesJson

from ..utils import (
    GITLAB_BRANCH_TEST_BRANCH,
    GITLAB_REPO,
    GITLAB_URL,
    with_temporary_folder,
)


def test_modules_install_nopipeline(self):
    """Test installing a module - no pipeline given"""
    self.mods_install.dir = None
    assert self.mods_install.install("foo") is False


@with_temporary_folder
def test_modules_install_emptypipeline(self, tmpdir):
    """Test installing a module - empty dir given"""
    self.mods_install.dir = tmpdir
    with pytest.raises(UserWarning) as excinfo:
        self.mods_install.install("foo")
    assert "Could not find a 'main.nf' or 'nextflow.config' file" in str(excinfo.value)


def test_modules_install_nomodule(self):
    """Test installing a module - unrecognised module given"""
    assert self.mods_install.install("foo") is False


def test_modules_install_trimgalore(self):
    """Test installing a module - TrimGalore!"""
    assert self.mods_install.install("trimgalore") is not False
    module_path = os.path.join(self.mods_install.dir, "modules", "nf-core", "modules", "trimgalore")
    assert os.path.exists(module_path)


def test_modules_install_trimgalore_twice(self):
    """Test installing a module - TrimGalore! already there"""
    self.mods_install.install("trimgalore")
    assert self.mods_install.install("trimgalore") is True


def test_modules_install_from_gitlab(self):
    """Test installing a module from GitLab"""
    assert self.mods_install_gitlab.install("fastqc") is True


def test_modules_install_different_branch_fail(self):
    """Test installing a module from a different branch"""
    install_obj = ModuleInstall(self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH)
    # The FastQC module does not exists in the branch-test branch
    assert install_obj.install("fastqc") is False


def test_modules_install_different_branch_succeed(self):
    """Test installing a module from a different branch"""
    install_obj = ModuleInstall(self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH)
    # The fastp module does exists in the branch-test branch
    assert install_obj.install("fastp") is True

    # Verify that the branch entry was added correctly
    modules_json = ModulesJson(self.pipeline_dir)
    assert modules_json.get_module_branch("fastp", GITLAB_REPO) == GITLAB_BRANCH_TEST_BRANCH
