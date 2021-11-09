#!/usr/bin/env python
""" Tests covering for utility functions.
"""

import nf_core.create
import nf_core.list
import nf_core.utils

import mock
import os
import pytest
import requests
import tempfile
import unittest
import shutil

from .utils import with_temporary_folder


class TestUtils(unittest.TestCase):
    """Class for utils tests"""

    def setUp(self):
        """Function that runs at start of tests for common resources

        Use nf_core.create() to make a pipeline that we can use for testing
        """
        self.tmp_dir = tempfile.mkdtemp()
        self.test_pipeline_dir = os.path.join(self.tmp_dir, "nf-core-testpipeline")
        self.create_obj = nf_core.create.PipelineCreate(
            "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=self.test_pipeline_dir
        )
        self.create_obj.init_pipeline()
        # Base Pipeline object on this directory
        self.pipeline_obj = nf_core.utils.Pipeline(self.test_pipeline_dir)

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_check_if_outdated_1(self):
        current_version = "1.0"
        remote_version = "2.0"
        is_outdated, current, remote = nf_core.utils.check_if_outdated(current_version, remote_version)
        assert is_outdated

    def test_check_if_outdated_2(self):
        current_version = "2.0"
        remote_version = "2.0"
        is_outdated, current, remote = nf_core.utils.check_if_outdated(current_version, remote_version)
        assert not is_outdated

    def test_check_if_outdated_3(self):
        current_version = "2.0.1"
        remote_version = "2.0.2"
        is_outdated, current, remote = nf_core.utils.check_if_outdated(current_version, remote_version)
        assert is_outdated

    def test_check_if_outdated_4(self):
        current_version = "1.10.dev0"
        remote_version = "1.7"
        is_outdated, current, remote = nf_core.utils.check_if_outdated(current_version, remote_version)
        assert not is_outdated

    def test_check_if_outdated_5(self):
        current_version = "1.10.dev0"
        remote_version = "1.11"
        is_outdated, current, remote = nf_core.utils.check_if_outdated(current_version, remote_version)
        assert is_outdated

    def test_rich_force_colours_false(self):
        os.environ.pop("GITHUB_ACTIONS", None)
        os.environ.pop("FORCE_COLOR", None)
        os.environ.pop("PY_COLORS", None)
        assert nf_core.utils.rich_force_colors() is None

    def test_rich_force_colours_true(self):
        os.environ["GITHUB_ACTIONS"] = "1"
        os.environ.pop("FORCE_COLOR", None)
        os.environ.pop("PY_COLORS", None)
        assert nf_core.utils.rich_force_colors() is True

    def test_load_pipeline_config(self):
        """Load the pipeline Nextflow config"""
        self.pipeline_obj._load_pipeline_config()
        assert self.pipeline_obj.nf_config["dag.enabled"] == "true"

    # TODO nf-core: Assess and strip out if no longer required for DSL2

    # def test_load_conda_env(self):
    #     """Load the pipeline Conda environment.yml file"""
    #     self.pipeline_obj._load_conda_environment()
    #     assert self.pipeline_obj.conda_config["channels"] == ["conda-forge", "bioconda", "defaults"]

    def test_list_files_git(self):
        """Test listing pipeline files using `git ls`"""
        self.pipeline_obj._list_files()
        assert os.path.join(self.test_pipeline_dir, "main.nf") in self.pipeline_obj.files

    @with_temporary_folder
    def test_list_files_no_git(self, tmpdir):
        """Test listing pipeline files without `git-ls`"""
        # Create a test file in a temporary directory
        tmp_fn = os.path.join(tmpdir, "testfile")
        open(tmp_fn, "a").close()
        pipeline_obj = nf_core.utils.Pipeline(tmpdir)
        pipeline_obj._list_files()
        assert tmp_fn in pipeline_obj.files

    @mock.patch("os.path.exists")
    @mock.patch("os.makedirs")
    def test_request_cant_create_cache(self, mock_mkd, mock_exists):
        """Test that we don't get an error when we can't create cachedirs"""
        mock_mkd.side_effect = PermissionError()
        mock_exists.return_value = False
        nf_core.utils.setup_requests_cachedir()

    def test_pip_package_pass(self):
        result = nf_core.utils.pip_package("multiqc=1.10")
        assert type(result) == dict

    @mock.patch("requests.get")
    def test_pip_package_timeout(self, mock_get):
        """Tests the PyPi connection and simulates a request timeout, which should
        return in an addiional warning in the linting"""
        # Define the behaviour of the request get mock
        mock_get.side_effect = requests.exceptions.Timeout()
        # Now do the test
        with pytest.raises(LookupError):
            nf_core.utils.pip_package("multiqc=1.10")

    @mock.patch("requests.get")
    def test_pip_package_connection_error(self, mock_get):
        """Tests the PyPi connection and simulates a connection error, which should
        result in an additional warning, as we cannot test if dependent module is latest"""
        # Define the behaviour of the request get mock
        mock_get.side_effect = requests.exceptions.ConnectionError()
        # Now do the test
        with pytest.raises(LookupError):
            nf_core.utils.pip_package("multiqc=1.10")

    def test_pip_erroneous_package(self):
        """Tests the PyPi API package information query"""
        with pytest.raises(ValueError):
            nf_core.utils.pip_package("not_a_package=1.0")

    def test_get_repo_releases_branches_nf_core(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline, wf_releases, wf_branches = nf_core.utils.get_repo_releases_branches("methylseq", wfs)
        for r in wf_releases:
            if r.get("tag_name") == "1.6":
                break
        else:
            raise AssertionError("Release 1.6 not found")
        assert "dev" in wf_branches.keys()

    def test_get_repo_releases_branches_not_nf_core(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline, wf_releases, wf_branches = nf_core.utils.get_repo_releases_branches("ewels/MultiQC", wfs)
        for r in wf_releases:
            if r.get("tag_name") == "v1.10":
                break
        else:
            raise AssertionError("MultiQC release v1.10 not found")
        assert "master" in wf_branches.keys()

    @pytest.mark.xfail(raises=AssertionError, strict=True)
    def test_get_repo_releases_branches_not_exists(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline, wf_releases, wf_branches = nf_core.utils.get_repo_releases_branches("made_up_pipeline", wfs)

    @pytest.mark.xfail(raises=AssertionError, strict=True)
    def test_get_repo_releases_branches_not_exists_slash(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline, wf_releases, wf_branches = nf_core.utils.get_repo_releases_branches("made-up/pipeline", wfs)
