import os

import pytest
import requests_cache
import responses

import nf_core.modules

from ..utils import mock_anaconda_api_calls, mock_biocontainers_api_calls


def test_modules_create_succeed(pipeline_dir):
    """Succeed at creating the TrimGalore! module"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "trim-galore", "0.6.7")
        mock_biocontainers_api_calls(rsps, "trim-galore", "0.6.7")
        module_create = nf_core.modules.ModuleCreate(
            pipeline_dir, "trimgalore", "@author", "process_single", True, True, conda_name="trim-galore"
        )
        with requests_cache.disabled():
            module_create.create()
    assert os.path.exists(os.path.join(pipeline_dir, "modules", "local", "trimgalore.nf"))


def test_modules_create_fail_exists(pipeline_dir):
    """Fail at creating the same module twice"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "trim-galore", "0.6.7")
        mock_biocontainers_api_calls(rsps, "trim-galore", "0.6.7")
        module_create = nf_core.modules.ModuleCreate(
            pipeline_dir, "trimgalore", "@author", "process_single", False, False, conda_name="trim-galore"
        )
        with requests_cache.disabled():
            module_create.create()
        with pytest.raises(UserWarning) as excinfo:
            with requests_cache.disabled():
                module_create.create()
    assert "Module file exists already" in str(excinfo.value)


def test_modules_create_nfcore_modules(local_modules_repo):
    """Create a module in nf-core/modules clone"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "fastqc", "0.11.9")
        mock_biocontainers_api_calls(rsps, "fastqc", "0.11.9")
        module_create = nf_core.modules.ModuleCreate(
            local_modules_repo, "fastqc", "@author", "process_low", False, False
        )
        with requests_cache.disabled():
            module_create.create()
    assert os.path.exists(os.path.join(local_modules_repo, "modules", "nf-core", "fastqc", "main.nf"))
    assert os.path.exists(os.path.join(local_modules_repo, "tests", "modules", "nf-core", "fastqc", "main.nf"))


def test_modules_create_nfcore_modules_subtool(local_modules_repo):
    """Create a tool/subtool module in a nf-core/modules clone"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "star", "2.8.10a")
        mock_biocontainers_api_calls(rsps, "star", "2.8.10a")
        module_create = nf_core.modules.ModuleCreate(
            local_modules_repo, "star/index", "@author", "process_medium", False, False
        )
        with requests_cache.disabled():
            module_create.create()
    assert os.path.exists(os.path.join(local_modules_repo, "modules", "nf-core", "star", "index", "main.nf"))
    assert os.path.exists(os.path.join(local_modules_repo, "tests", "modules", "nf-core", "star", "index", "main.nf"))
