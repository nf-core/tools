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


# A skeleton object with the passed/warned/failed list attrs
# Use this in place of a ModuleLint object to test behaviour of
# linting methods which don't need the full setup
class MockModuleLint:
    def __init__(self):
        self.passed = []
        self.warned = []
        self.failed = []

        self.main_nf = "main_nf"


class TestModulesLint(TestModules):
    """Core ModuleLint functionality tests"""

    def test_modules_lint_init(self):
        """Test ModuleLint initialization"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        assert module_lint.directory == self.pipeline_dir
        assert hasattr(module_lint, 'passed')
        assert hasattr(module_lint, 'warned')
        assert hasattr(module_lint, 'failed')

    def test_mock_module_lint(self):
        """Test MockModuleLint utility class"""
        mock_lint = MockModuleLint()
        assert isinstance(mock_lint.passed, list)
        assert isinstance(mock_lint.warned, list)
        assert isinstance(mock_lint.failed, list)
        assert mock_lint.main_nf == "main_nf"
