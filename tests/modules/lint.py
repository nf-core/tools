import os

import pytest

import nf_core.modules

from ..utils import GITLAB_URL
from .patch import BISMARK_ALIGN, PATCH_BRANCH, setup_patch


def test_modules_lint_trimgalore(self):
    """Test linting the TrimGalore! module"""
    self.mods_install.install("trimgalore")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
    module_lint.lint(print_results=False, module="trimgalore")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_empty(self):
    """Test linting a pipeline with no modules installed"""
    self.mods_remove.remove("fastqc")
    self.mods_remove.remove("multiqc")
    self.mods_remove.remove("custom/dumpsoftwareversions")
    with pytest.raises(LookupError):
        nf_core.modules.ModuleLint(dir=self.pipeline_dir)


def test_modules_lint_new_modules(self):
    """lint all modules in nf-core/modules repo clone"""
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=True, all_modules=True)
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_no_gitlab(self):
    """Test linting a pipeline with no modules installed"""
    with pytest.raises(LookupError):
        nf_core.modules.ModuleLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)


def test_modules_lint_gitlab_modules(self):
    """Lint modules from a different remote"""
    self.mods_install_gitlab.install("fastqc")
    self.mods_install_gitlab.install("multiqc")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)
    module_lint.lint(print_results=False, all_modules=True)
    assert len(module_lint.failed) == 0
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_patched_modules(self):
    """
    Test creating a patch file and applying it to a new version of the the files
    """
    setup_patch(self.pipeline_dir, True)

    # Create a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(BISMARK_ALIGN)

    # change temporarily working directory to the pipeline directory
    # to avoid error from try_apply_patch() during linting
    wd_old = os.getcwd()
    os.chdir(self.pipeline_dir)
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)
    module_lint.lint(print_results=False, all_modules=True)
    os.chdir(wd_old)

    assert len(module_lint.failed) == 0
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
