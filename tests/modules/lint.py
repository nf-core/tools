from pathlib import Path

import nf_core.modules

from ..utils import GITLAB_REPO, GITLAB_URL
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
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
    module_lint.lint(print_results=False, all_modules=True)
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) == 0
    assert len(module_lint.warned) == 0


def test_modules_lint_new_modules(self):
    """lint all modules in nf-core/modules repo clone"""
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=True, all_modules=True)
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_patch_invalid(self):
    """Try linting a module that has a corrupted patch file"""
    # Install the trimgalore module and modify it
    setup_patch(self.pipeline_dir, True)

    # Create the patch file
    nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH).patch(BISMARK_ALIGN)

    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)

    # Modify the file
    patch_path = Path(
        self.pipeline_dir, "modules", GITLAB_REPO, BISMARK_ALIGN, f"{BISMARK_ALIGN.replace('/', '-')}.diff"
    )
    with open(patch_path, "r") as fh:
        org_lines = fh.readlines()

    mod_lines = org_lines.copy()
    for i, line in enumerate(mod_lines):
        if line.startswith("+++"):
            mod_lines.pop(i)
            break
    with open(patch_path, "w") as fh:
        fh.writelines(mod_lines)

    module_lint.lint(print_results=False, module=BISMARK_ALIGN)
    assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0

    mod_lines = org_lines.copy()
    for i, line in enumerate(mod_lines):
        if line.startswith("@@"):
            mod_lines.pop(i)
            break
    with open(patch_path, "w") as fh:
        fh.writelines(mod_lines)

    module_lint.lint(print_results=False, module=BISMARK_ALIGN)
    assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
