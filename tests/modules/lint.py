import os
from pathlib import Path

import pytest

import nf_core.modules
from nf_core.modules.lint import main_nf

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
    """lint a new module"""
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
    assert len(module_lint.failed) == 2
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_multiple_remotes(self):
    """Lint modules from a different remote"""
    self.mods_install_gitlab.install("multiqc")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)
    module_lint.lint(print_results=False, all_modules=True)
    assert len(module_lint.failed) == 1
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_registry(self):
    """Test linting the samtools module and alternative registry"""
    self.mods_install.install("samtools")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir, registry="public.ecr.aws")
    module_lint.lint(print_results=False, module="samtools")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
    module_lint.lint(print_results=False, module="samtools")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
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

    assert len(module_lint.failed) == 1
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


# A skeleton object with the passed/warned/failed list attrs
# Use this in place of a ModuleLint object to test behaviour of
# linting methods which don't need the full setup
class MockModuleLint:
    def __init__(self):
        self.passed = []
        self.warned = []
        self.failed = []

        self.main_nf = "main_nf"


PROCESS_LABEL_GOOD = (
    """
    label 'process_high'
    cpus 12
    """,
    1,
    0,
    0,
)
PROCESS_LABEL_NON_ALPHANUMERIC = (
    """
    label 'a:label:with:colons'
    cpus 12
    """,
    0,
    2,
    0,
)
PROCESS_LABEL_GOOD_CONFLICTING = (
    """
    label 'process_high'
    label 'process_low'
    cpus 12
    """,
    0,
    1,
    0,
)
PROCESS_LABEL_GOOD_DUPLICATES = (
    """
    label 'process_high'
    label 'process_high'
    cpus 12
    """,
    0,
    2,
    0,
)
PROCESS_LABEL_GOOD_AND_NONSTANDARD = (
    """
    label 'process_high'
    label 'process_extra_label'
    cpus 12
    """,
    1,
    1,
    0,
)
PROCESS_LABEL_NONSTANDARD = (
    """
    label 'process_extra_label'
    cpus 12
    """,
    0,
    2,
    0,
)
PROCESS_LABEL_NONSTANDARD_DUPLICATES = (
    """
    label process_extra_label
    label process_extra_label
    cpus 12
    """,
    0,
    3,
    0,
)
PROCESS_LABEL_NONE_FOUND = (
    """
    cpus 12
    """,
    0,
    1,
    0,
)

PROCESS_LABEL_TEST_CASES = [
    PROCESS_LABEL_GOOD,
    PROCESS_LABEL_NON_ALPHANUMERIC,
    PROCESS_LABEL_GOOD_CONFLICTING,
    PROCESS_LABEL_GOOD_DUPLICATES,
    PROCESS_LABEL_GOOD_AND_NONSTANDARD,
    PROCESS_LABEL_NONSTANDARD,
    PROCESS_LABEL_NONSTANDARD_DUPLICATES,
    PROCESS_LABEL_NONE_FOUND,
]


def test_modules_lint_check_process_labels(self):
    for test_case in PROCESS_LABEL_TEST_CASES:
        process, passed, warned, failed = test_case
        mocked_ModuleLint = MockModuleLint()
        main_nf.check_process_labels(mocked_ModuleLint, process.splitlines())
        assert len(mocked_ModuleLint.passed) == passed
        assert len(mocked_ModuleLint.warned) == warned
        assert len(mocked_ModuleLint.failed) == failed
