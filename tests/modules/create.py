import os
import shutil
from pathlib import Path
from unittest import mock

import pytest
import requests_cache
import responses
import yaml
from git.repo import Repo

import nf_core.modules
from tests.utils import (
    GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH,
    GITLAB_URL,
    mock_anaconda_api_calls,
    mock_biocontainers_api_calls,
)


def test_modules_create_succeed(self):
    """Succeed at creating the TrimGalore! module"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "trim-galore", "0.6.7")
        mock_biocontainers_api_calls(rsps, "trim-galore", "0.6.7")
        module_create = nf_core.modules.ModuleCreate(
            self.pipeline_dir, "trimgalore", "@author", "process_single", True, True, conda_name="trim-galore"
        )
        with requests_cache.disabled():
            module_create.create()
    assert os.path.exists(os.path.join(self.pipeline_dir, "modules", "local", "trimgalore.nf"))


def test_modules_create_fail_exists(self):
    """Fail at creating the same module twice"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "trim-galore", "0.6.7")
        mock_biocontainers_api_calls(rsps, "trim-galore", "0.6.7")
        module_create = nf_core.modules.ModuleCreate(
            self.pipeline_dir, "trimgalore", "@author", "process_single", False, False, conda_name="trim-galore"
        )
        with requests_cache.disabled():
            module_create.create()
        with pytest.raises(UserWarning) as excinfo:
            with requests_cache.disabled():
                module_create.create()
    assert "Module file exists already" in str(excinfo.value)


def test_modules_create_nfcore_modules(self):
    """Create a module in nf-core/modules clone"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "fastqc", "0.11.9")
        mock_biocontainers_api_calls(rsps, "fastqc", "0.11.9")
        module_create = nf_core.modules.ModuleCreate(
            self.nfcore_modules, "fastqc", "@author", "process_low", False, False
        )
        with requests_cache.disabled():
            module_create.create()
    assert os.path.exists(os.path.join(self.nfcore_modules, "modules", "nf-core", "fastqc", "main.nf"))
    assert os.path.exists(os.path.join(self.nfcore_modules, "modules", "nf-core", "fastqc", "tests", "main.nf.test"))


def test_modules_create_nfcore_modules_subtool(self):
    """Create a tool/subtool module in a nf-core/modules clone"""
    with responses.RequestsMock() as rsps:
        mock_anaconda_api_calls(rsps, "star", "2.8.10a")
        mock_biocontainers_api_calls(rsps, "star", "2.8.10a")
        module_create = nf_core.modules.ModuleCreate(
            self.nfcore_modules, "star/index", "@author", "process_medium", False, False
        )
        with requests_cache.disabled():
            module_create.create()
    assert os.path.exists(os.path.join(self.nfcore_modules, "modules", "nf-core", "star", "index", "main.nf"))
    assert os.path.exists(
        os.path.join(self.nfcore_modules, "modules", "nf-core", "star", "index", "tests", "main.nf.test")
    )


@mock.patch("rich.prompt.Confirm.ask")
def test_modules_migrate(self, mock_rich_ask):
    """Create a module with the --migrate-pytest option to convert pytest to nf-test"""
    pytest_dir = Path(self.nfcore_modules, "tests", "modules", "nf-core", "samtools", "sort")
    module_dir = Path(self.nfcore_modules, "modules", "nf-core", "samtools", "sort")

    # Clone modules repo with pytests
    shutil.rmtree(self.nfcore_modules)
    Repo.clone_from(GITLAB_URL, self.nfcore_modules, branch=GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH)
    with open(module_dir / "main.nf") as fh:
        old_main_nf = fh.read()
    with open(module_dir / "meta.yml") as fh:
        old_meta_yml = fh.read()

    # Create a module with --migrate-pytest
    mock_rich_ask.return_value = True
    module_create = nf_core.modules.ModuleCreate(self.nfcore_modules, "samtools/sort", migrate_pytest=True)
    module_create.create()

    with open(module_dir / "main.nf") as fh:
        new_main_nf = fh.read()
    with open(module_dir / "meta.yml") as fh:
        new_meta_yml = fh.read()
    nextflow_config = module_dir / "tests" / "nextflow.config"

    # Check that old files have been copied to the new module
    assert old_main_nf == new_main_nf
    assert old_meta_yml == new_meta_yml
    assert nextflow_config.is_file()

    # Check that pytest folder is deleted
    assert not pytest_dir.is_dir()

    # Check that pytest_modules.yml is updated
    with open(Path(self.nfcore_modules, "tests", "config", "pytest_modules.yml")) as fh:
        modules_yml = yaml.safe_load(fh)
    assert "samtools/sort" not in modules_yml.keys()


@mock.patch("rich.prompt.Confirm.ask")
def test_modules_migrate_no_delete(self, mock_rich_ask):
    """Create a module with the --migrate-pytest option to convert pytest to nf-test.
    Test that pytest directory is not deleted."""
    pytest_dir = Path(self.nfcore_modules, "tests", "modules", "nf-core", "samtools", "sort")

    # Clone modules repo with pytests
    shutil.rmtree(self.nfcore_modules)
    Repo.clone_from(GITLAB_URL, self.nfcore_modules, branch=GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH)

    # Create a module with --migrate-pytest
    mock_rich_ask.return_value = False
    module_create = nf_core.modules.ModuleCreate(self.nfcore_modules, "samtools/sort", migrate_pytest=True)
    module_create.create()

    # Check that pytest folder is not deleted
    assert pytest_dir.is_dir()

    # Check that pytest_modules.yml is updated
    with open(Path(self.nfcore_modules, "tests", "config", "pytest_modules.yml")) as fh:
        modules_yml = yaml.safe_load(fh)
    assert "samtools/sort" not in modules_yml.keys()


@mock.patch("rich.prompt.Confirm.ask")
def test_modules_migrate_symlink(self, mock_rich_ask):
    """Create a module with the --migrate-pytest option to convert pytest with symlinks to nf-test.
    Test that the symlink is deleted and the file is copied."""

    pytest_dir = Path(self.nfcore_modules, "tests", "modules", "nf-core", "samtools", "sort")
    module_dir = Path(self.nfcore_modules, "modules", "nf-core", "samtools", "sort")

    # Clone modules repo with pytests
    shutil.rmtree(self.nfcore_modules)
    Repo.clone_from(GITLAB_URL, self.nfcore_modules, branch=GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH)

    # Create a symlinked file in the pytest directory
    symlink_file = pytest_dir / "symlink_file.txt"
    symlink_file.symlink_to(module_dir / "main.nf")

    # Create a module with --migrate-pytest
    mock_rich_ask.return_value = True
    module_create = nf_core.modules.ModuleCreate(self.nfcore_modules, "samtools/sort", migrate_pytest=True)
    module_create.create()

    # Check that symlink is deleted
    assert not symlink_file.is_symlink()
