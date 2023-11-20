"""Test the 'subworkflows test' command which runs module pytests."""
import os
import shutil
from pathlib import Path

import pytest

import nf_core.subworkflows

from ..utils import set_wd


def test_subworkflows_test_no_installed_subworkflows(self):
    """Test the check_inputs() function - raise UserWarning because installed modules were not found"""
    with set_wd(self.nfcore_modules):
        module_dir = Path(self.nfcore_modules, "subworkflows")
        shutil.rmtree(module_dir)
        module_dir.mkdir()
        meta_builder = nf_core.subworkflows.SubworkflowsTest(None, False, "")
        meta_builder.repo_type = "modules"
        with pytest.raises(UserWarning) as excinfo:
            meta_builder._check_inputs()
    assert "No installed subworkflows were found" in str(excinfo.value)
