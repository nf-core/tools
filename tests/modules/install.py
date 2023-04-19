import os

import pytest

from nf_core.modules.install import ModuleInstall
from nf_core.modules.modules_json import ModulesJson

from ..utils import (
    GITLAB_BRANCH_ORG_PATH_BRANCH,
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
    os.mkdir(os.path.join(tmpdir, "nf-core-pipe"))
    self.mods_install.dir = os.path.join(tmpdir, "nf-core-pipe")
    with pytest.raises(UserWarning) as excinfo:
        self.mods_install.install("foo")
    assert "Could not find a 'main.nf' or 'nextflow.config' file" in str(excinfo.value)


def test_modules_install_nomodule(self):
    """Test installing a module - unrecognised module given"""
    assert self.mods_install.install("foo") is False


def test_modules_install_trimgalore(self):
    """Test installing a module - TrimGalore!"""
    assert self.mods_install.install("trimgalore") is not False
    module_path = os.path.join(self.mods_install.dir, "modules", "nf-core", "trimgalore")
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
    assert (
        modules_json.get_component_branch(self.component_type, "fastp", GITLAB_URL, GITLAB_REPO)
        == GITLAB_BRANCH_TEST_BRANCH
    )


def test_modules_install_tracking(self):
    """Test installing a module and finding 'modules' in the installed_by section of modules.json"""
    self.mods_install.install("trimgalore")

    # Verify that the installed_by entry was added correctly
    modules_json = ModulesJson(self.pipeline_dir)
    mod_json = modules_json.get_modules_json()
    assert mod_json["repos"]["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]["trimgalore"][
        "installed_by"
    ] == ["modules"]


def test_modules_install_alternate_remote(self):
    """Test installing a module from a different remote with the same organization path"""
    install_obj = ModuleInstall(self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_ORG_PATH_BRANCH)
    # Install fastqc from GitLab which is also installed from GitHub with the same org_path
    with pytest.raises(Exception) as excinfo:
        install_obj.install("fastqc")
        assert "Could not find a 'main.nf' or 'nextflow.config' file" in str(excinfo.value)
