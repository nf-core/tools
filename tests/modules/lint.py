import os
from pathlib import Path

import pytest

import nf_core.modules

from ..utils import GITLAB_URL, set_wd
from .patch import BISMARK_ALIGN, CORRECT_SHA, PATCH_BRANCH, REPO_NAME, modify_main_nf


def setup_patch(pipeline_dir, modify_module):
    install_obj = nf_core.modules.ModuleInstall(
        pipeline_dir, prompt=False, force=False, remote_url=GITLAB_URL, branch=PATCH_BRANCH, sha=CORRECT_SHA
    )

    # Install the module
    install_obj.install(BISMARK_ALIGN)

    if modify_module:
        # Modify the module
        module_path = Path(pipeline_dir, "modules", REPO_NAME, BISMARK_ALIGN)
        modify_main_nf(module_path / "main.nf")


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
    self.mods_remove.remove("fastqc", force=True)
    self.mods_remove.remove("multiqc", force=True)
    self.mods_remove.remove("custom/dumpsoftwareversions", force=True)
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
    self.mods_remove.remove("fastqc", force=True)
    self.mods_remove.remove("multiqc", force=True)
    self.mods_remove.remove("custom/dumpsoftwareversions", force=True)
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


def test_modules_lint_multiple_remotes(self):
    """Lint modules from a different remote"""
    self.mods_install.install("fastqc")
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
    with set_wd(self.pipeline_dir):
        module_lint = nf_core.modules.ModuleLint(
            dir=self.pipeline_dir, remote_url=GITLAB_URL, branch=PATCH_BRANCH, hide_progress=True
        )
        module_lint.lint(
            print_results=False,
            all_modules=True,
        )

    assert len(module_lint.failed) == 0
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
