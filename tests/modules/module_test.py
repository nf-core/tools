"""Test the 'modules test' command which runs module pytests."""
import os
import shutil
from pathlib import Path

import pytest

import nf_core.modules


def test_modules_test_check_inputs(self):
    """Test the check_inputs() function - raise UserWarning because module doesn't exist"""
    cwd = os.getcwd()
    os.chdir(self.nfcore_modules)
    meta_builder = nf_core.modules.ModulesTest("none", True, "")
    with pytest.raises(UserWarning) as excinfo:
        meta_builder._check_inputs()
    os.chdir(cwd)
    assert "Cannot find directory" in str(excinfo.value)


def test_modules_test_no_name_no_prompts(self):
    """Test the check_inputs() function - raise UserWarning prompts are deactivated and module name is not provided."""
    cwd = os.getcwd()
    os.chdir(self.nfcore_modules)
    meta_builder = nf_core.modules.ModulesTest(None, True, "")
    with pytest.raises(UserWarning) as excinfo:
        meta_builder._check_inputs()
    os.chdir(cwd)
    assert "Tool name not provided and prompts deactivated." in str(excinfo.value)


def test_modules_test_no_installed_modules(self):
    """Test the check_inputs() function - raise UserWarning because installed modules were not found"""
    cwd = os.getcwd()
    os.chdir(self.nfcore_modules)
    module_dir = Path(self.nfcore_modules, "modules")
    shutil.rmtree(module_dir)
    module_dir.mkdir()
    meta_builder = nf_core.modules.ModulesTest(None, False, "")
    meta_builder.repo_type = "modules"
    with pytest.raises(UserWarning) as excinfo:
        meta_builder._check_inputs()
    os.chdir(cwd)
    assert "No installed modules were found" in str(excinfo.value)
