import os

import pytest
import requests_mock

import nf_core.modules
from tests.utils import mock_api_calls


def test_modules_create_succeed(self):
    """Succeed at creating the TrimGalore! module"""
    with requests_mock.Mocker() as mock:
        mock_api_calls(mock, "trim-galore", "0.6.7")
        module_create = nf_core.modules.ModuleCreate(
            self.pipeline_dir, "trimgalore", "@author", "process_single", True, True, conda_name="trim-galore"
        )
        module_create.create()
    assert os.path.exists(os.path.join(self.pipeline_dir, "modules", "local", "trimgalore.nf"))


def test_modules_create_fail_exists(self):
    """Fail at creating the same module twice"""
    with requests_mock.Mocker() as mock:
        mock_api_calls(mock, "trim-galore", "0.6.7")
        module_create = nf_core.modules.ModuleCreate(
            self.pipeline_dir, "trimgalore", "@author", "process_single", False, False, conda_name="trim-galore"
        )
        module_create.create()
        with pytest.raises(UserWarning) as excinfo:
            module_create.create()
    assert "Module file exists already" in str(excinfo.value)


def test_modules_create_nfcore_modules(self):
    """Create a module in nf-core/modules clone"""
    with requests_mock.Mocker() as mock:
        mock_api_calls(mock, "fastqc", "0.11.9")
        module_create = nf_core.modules.ModuleCreate(
            self.nfcore_modules, "fastqc", "@author", "process_low", False, False
        )
        module_create.create()
    assert os.path.exists(os.path.join(self.nfcore_modules, "modules", "nf-core", "fastqc", "main.nf"))
    assert os.path.exists(os.path.join(self.nfcore_modules, "tests", "modules", "nf-core", "fastqc", "main.nf"))


def test_modules_create_nfcore_modules_subtool(self):
    """Create a tool/subtool module in a nf-core/modules clone"""
    with requests_mock.Mocker() as mock:
        mock_api_calls(mock, "star", "2.8.10a")
        module_create = nf_core.modules.ModuleCreate(
            self.nfcore_modules, "star/index", "@author", "process_medium", False, False
        )
        module_create.create()
    assert os.path.exists(os.path.join(self.nfcore_modules, "modules", "nf-core", "star", "index", "main.nf"))
    assert os.path.exists(os.path.join(self.nfcore_modules, "tests", "modules", "nf-core", "star", "index", "main.nf"))
