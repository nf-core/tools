import json
import shutil
from pathlib import Path
from typing import Union

import yaml
from git.repo import Repo

import nf_core.modules.lint
from nf_core.utils import set_wd

from ...test_modules import TestModules
from ...utils import GITLAB_NFTEST_BRANCH, GITLAB_URL


class TestModulesLintIntegration(TestModules):
    """Test the overall ModuleLint functionality with different modules"""

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

    def test_modules_lint_new_modules(self):
        """lint a new module"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0 