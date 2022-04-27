"""Test the 'modules test' command which runs module pytests."""
import os
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
