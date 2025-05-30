import json
import shutil
from pathlib import Path
from typing import Union

import yaml
from git.repo import Repo

import nf_core.modules.lint
from nf_core.modules.lint.main_nf import check_container_link_line, check_process_labels
from nf_core.utils import set_wd

from ...test_modules import TestModules
from ...utils import GITLAB_NFTEST_BRANCH, GITLAB_URL

class TestModulesLint(TestModules):

    def test_modules_lint_trimgalore(self):
        """Test linting the TrimGalore! module"""
        self.mods_install.install("trimgalore")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="trimgalore")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_trinity(self):
        """Test linting the Trinity module"""
        self.mods_install.install("trinity")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="trinity")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_tabix_tabix(self):
        """Test linting the tabix/tabix module"""
        self.mods_install.install("tabix/tabix")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="tabix/tabix")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_empty(self):
        """Test linting a pipeline with no modules installed"""
        self.mods_remove.remove("fastqc", force=True)
        self.mods_remove.remove("multiqc", force=True)
        nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        assert "No modules from https://github.com/nf-core/modules.git installed in pipeline" in self.caplog.text

    def test_modules_lint_new_modules(self):
        """lint a new module"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_no_gitlab(self):
        """Test linting a pipeline with no modules installed"""
        self.mods_remove.remove("fastqc", force=True)
        self.mods_remove.remove("multiqc", force=True)
        nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, remote_url=GITLAB_URL)
        assert f"No modules from {GITLAB_URL} installed in pipeline" in self.caplog.text

    def test_modules_lint_gitlab_modules(self):
        """Lint modules from a different remote"""
        self.mods_install_gitlab.install("fastqc")
        self.mods_install_gitlab.install("multiqc")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, remote_url=GITLAB_URL)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.failed) == 2
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_multiple_remotes(self):
        """Lint modules from a different remote"""
        self.mods_install_gitlab.install("multiqc")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, remote_url=GITLAB_URL)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.failed) == 1
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0


    def test_modules_lint_local(self):
        assert self.mods_install.install("trimgalore")
        installed = Path(self.pipeline_dir, "modules", "nf-core", "trimgalore")
        local = Path(self.pipeline_dir, "modules", "local", "trimgalore")
        shutil.move(installed, local)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, local=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_local_missing_files(self):
        assert self.mods_install.install("trimgalore")
        installed = Path(self.pipeline_dir, "modules", "nf-core", "trimgalore")
        local = Path(self.pipeline_dir, "modules", "local", "trimgalore")
        shutil.move(installed, local)
        Path(self.pipeline_dir, "modules", "local", "trimgalore", "environment.yml").unlink()
        Path(self.pipeline_dir, "modules", "local", "trimgalore", "meta.yml").unlink()
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, local=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        warnings = [x.message for x in module_lint.warned]
        assert "Module's `environment.yml` does not exist" in warnings
        assert "Module `meta.yml` does not exist" in warnings

    def test_modules_lint_local_old_format(self):
        Path(self.pipeline_dir, "modules", "local").mkdir()
        assert self.mods_install.install("trimgalore")
        installed = Path(self.pipeline_dir, "modules", "nf-core", "trimgalore", "main.nf")
        local = Path(self.pipeline_dir, "modules", "local", "trimgalore.nf")
        shutil.move(installed, local)
        self.mods_remove.remove("trimgalore", force=True)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, local=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
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
