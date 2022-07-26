#!/usr/bin/env python
""" Tests covering the sync command
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import git

import nf_core.create
import nf_core.sync

from .utils import with_temporary_folder


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        """Create a new pipeline to test"""
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.pipeline_dir = self.tmp_dir / "test_pipeline"
        self.create_obj = nf_core.create.PipelineCreate(
            "testing", "test pipeline", "tester", outdir=self.pipeline_dir, plain=True
        )
        self.create_obj.init_pipeline()

    def tearDown(self):
        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    @with_temporary_folder
    def test_inspect_sync_dir_notgit(self, tmp_dir):
        """Try syncing an empty directory"""
        psync = nf_core.sync.PipelineSync(tmp_dir)
        try:
            psync.inspect_sync_dir()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.SyncException as e:
            assert "does not appear to be a git repository" in e.args[0]

    def test_inspect_sync_dir_dirty(self):
        """Try syncing a pipeline with uncommitted changes"""
        # Add an empty file, uncommitted
        test_fn = self.pipeline_dir / "uncommitted"
        test_fn.touch()
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        try:
            psync.inspect_sync_dir()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.SyncException as e:
            test_fn.unlink()
            assert e.args[0].startswith("Uncommitted changes found in pipeline directory!")
        except Exception as e:
            test_fn.unlink()
            raise e

    def test_get_wf_config_no_branch(self):
        """Try getting a workflow config when the branch doesn't exist"""
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir, from_branch="foo")
        try:
            psync.inspect_sync_dir()
            psync.get_wf_config()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.SyncException as e:
            assert e.args[0] == "Branch `foo` not found!"

    def test_get_wf_config_missing_required_config(self):
        """Try getting a workflow config, then make it miss a required config option"""
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.required_config_vars = ["fakethisdoesnotexist"]
        try:
            psync.inspect_sync_dir()
            psync.get_wf_config()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.SyncException as e:
            # Check that we did actually get some config back
            assert psync.wf_config["params.validate_params"] == "true"
            # Check that we raised because of the missing fake config var
            assert e.args[0] == "Workflow config variable `fakethisdoesnotexist` not found!"

    def test_checkout_template_branch(self):
        """Try checking out the TEMPLATE branch of the pipeline"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()

    def test_delete_template_branch_files(self):
        """Confirm that we can delete all files in the TEMPLATE branch"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()
        psync.delete_template_branch_files()
        pipeline_dir_content = {i.name for i in self.pipeline_dir.iterdir()}
        assert pipeline_dir_content == {".git"}

    def test_create_template_pipeline(self):
        """Confirm that we can delete all files in the TEMPLATE branch"""
        # First, delete all the files
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()
        psync.delete_template_branch_files()
        # Now create the new template
        psync.make_template_pipeline()
        pipeline_dir_content = {i.name for i in self.pipeline_dir.iterdir()}
        assert {"main.nf", "nextflow.config"}.issubset(pipeline_dir_content)

    def test_commit_template_changes_nochanges(self):
        """Try to commit the TEMPLATE branch, but no changes were made"""
        # Check out the TEMPLATE branch but skip making the new template etc.
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()
        # Function returns False if no changes were made
        assert psync.commit_template_changes() is False

    def test_commit_template_changes_changes(self):
        """Try to commit the TEMPLATE branch, but no changes were made"""
        # Check out the TEMPLATE branch but skip making the new template etc.
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()
        # Add an empty file, uncommitted
        test_fn = self.pipeline_dir / "uncommitted"
        test_fn.touch()
        # Check that we have uncommitted changes
        assert psync.repo.is_dirty(untracked_files=True) is True
        # Function returns True if no changes were made
        assert psync.commit_template_changes() is True
        # Check that we don't have any uncommitted changes
        assert psync.repo.is_dirty(untracked_files=True) is False

    def raise_git_exception(self):
        """Raise an exception from GitPython"""
        raise git.exc.GitCommandError("Test")

    def test_push_template_branch_error(self):
        """Try pushing the changes, but without a remote (should fail)"""
        # Check out the TEMPLATE branch but skip making the new template etc.
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()
        # Add an empty file and commit it
        test_fn = self.pipeline_dir / "uncommitted"
        test_fn.touch()
        psync.commit_template_changes()
        # Try to push changes
        try:
            psync.push_template_branch()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.PullRequestException as e:
            assert e.args[0].startswith("Could not push TEMPLATE branch")

    def mocked_requests_get(url, **kwargs):
        """Helper function to emulate POST requests responses from the web"""

        class MockResponse:
            def __init__(self, data, status_code):
                self.url = kwargs.get("url")
                self.status_code = status_code
                self.from_cache = False
                self.reason = "Mocked response"
                self.data = data
                self.content = json.dumps(data)
                self.headers = {"content-encoding": "test", "connection": "fake"}

            def json(self):
                return self.data

        url_template = "https://api.github.com/repos/{}/response/pulls?head=TEMPLATE&base=None"
        if url == url_template.format("no_existing_pr"):
            response_data = []
            return MockResponse(response_data, 200)

        return MockResponse({"html_url": url}, 404)

    def mocked_requests_patch(url, **kwargs):
        """Helper function to emulate POST requests responses from the web"""

        class MockResponse:
            def __init__(self, data, status_code):
                self.url = kwargs.get("url")
                self.status_code = status_code
                self.from_cache = False
                self.reason = "Mocked"
                self.content = json.dumps(data)
                self.headers = {"content-encoding": "test", "connection": "fake"}

        if url == "url_to_update_pr":
            response_data = {"html_url": "great_success"}
            return MockResponse(response_data, 200)

        return MockResponse({"patch_url": url}, 404)

    def mocked_requests_post(url, **kwargs):
        """Helper function to emulate POST requests responses from the web"""

        class MockResponse:
            def __init__(self, data, status_code):
                self.url = kwargs.get("url")
                self.status_code = status_code
                self.from_cache = False
                self.reason = "Mocked"
                self.data = data
                self.content = json.dumps(data)
                self.headers = {"content-encoding": "test", "connection": "fake"}

            def json(self):
                return self.data

        if url == "https://api.github.com/repos/no_existing_pr/response/pulls":
            response_data = {"html_url": "great_success"}
            return MockResponse(response_data, 201)

        response_data = {}
        return MockResponse(response_data, 404)

    @mock.patch("nf_core.utils.gh_api.get", side_effect=mocked_requests_get)
    @mock.patch("nf_core.utils.gh_api.post", side_effect=mocked_requests_post)
    def test_make_pull_request_success(self, mock_post, mock_get):
        """Try making a PR - successful response"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.gh_api.get = mock_get
        psync.gh_api.post = mock_post
        psync.gh_username = "no_existing_pr"
        psync.gh_repo = "no_existing_pr/response"
        os.environ["GITHUB_AUTH_TOKEN"] = "test"
        psync.make_pull_request()
        assert psync.gh_pr_returned_data["html_url"] == "great_success"

    @mock.patch("nf_core.utils.gh_api.get", side_effect=mocked_requests_get)
    @mock.patch("nf_core.utils.gh_api.post", side_effect=mocked_requests_post)
    def test_make_pull_request_bad_response(self, mock_post, mock_get):
        """Try making a PR and getting a 404 error"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.gh_api.get = mock_get
        psync.gh_api.post = mock_post
        psync.gh_username = "bad_url"
        psync.gh_repo = "bad_url/response"
        os.environ["GITHUB_AUTH_TOKEN"] = "test"
        try:
            psync.make_pull_request()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.PullRequestException as e:
            assert e.args[0].startswith("Something went badly wrong - GitHub API PR failed - got return code 404")
