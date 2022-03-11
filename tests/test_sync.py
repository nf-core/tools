#!/usr/bin/env python
""" Tests covering the sync command
"""

import nf_core.create
import nf_core.sync

import git
import json
import mock
import os
import shutil
import tempfile
import unittest

from .utils import with_temporary_folder


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        """Create a new pipeline to test"""
        self.tmp_dir = tempfile.mkdtemp()
        self.pipeline_dir = os.path.join(self.tmp_dir, "test_pipeline")
        self.create_obj = nf_core.create.PipelineCreate("testing", "test pipeline", "tester", outdir=self.pipeline_dir)
        self.create_obj.init_pipeline()

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
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
        test_fn = os.path.join(self.pipeline_dir, "uncommitted")
        open(test_fn, "a").close()
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        try:
            psync.inspect_sync_dir()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.SyncException as e:
            os.remove(test_fn)
            assert e.args[0].startswith("Uncommitted changes found in pipeline directory!")
        except Exception as e:
            os.remove(test_fn)
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
        assert os.listdir(self.pipeline_dir) == [".git"]

    def test_create_template_pipeline(self):
        """Confirm that we can delete all files in the TEMPLATE branch"""
        # First, delete all the files
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()
        psync.delete_template_branch_files()
        assert os.listdir(self.pipeline_dir) == [".git"]
        # Now create the new template
        psync.make_template_pipeline()
        assert "main.nf" in os.listdir(self.pipeline_dir)
        assert "nextflow.config" in os.listdir(self.pipeline_dir)

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
        test_fn = os.path.join(self.pipeline_dir, "uncommitted")
        open(test_fn, "a").close()
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
        test_fn = os.path.join(self.pipeline_dir, "uncommitted")
        open(test_fn, "a").close()
        psync.commit_template_changes()
        # Try to push changes
        try:
            psync.push_template_branch()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.PullRequestException as e:
            assert e.args[0].startswith("Could not push TEMPLATE branch")

    def mocked_requests_get(**kwargs):
        """Helper function to emulate POST requests responses from the web"""

        class MockResponse:
            def __init__(self, data, status_code):
                self.status_code = status_code
                self.content = json.dumps(data)

        url_template = "https://api.github.com/repos/{}/response/pulls?head=TEMPLATE&base=None"
        if kwargs["url"] == url_template.format("no_existing_pr"):
            response_data = []
            return MockResponse(response_data, 200)

        return MockResponse({"get_url": kwargs["url"]}, 404)

    def mocked_requests_patch(**kwargs):
        """Helper function to emulate POST requests responses from the web"""

        class MockResponse:
            def __init__(self, data, status_code):
                self.status_code = status_code
                self.content = json.dumps(data)

        if kwargs["url"] == "url_to_update_pr":
            response_data = {"html_url": "great_success"}
            return MockResponse(response_data, 200)

        return MockResponse({"patch_url": kwargs["url"]}, 404)

    def mocked_requests_post(**kwargs):
        """Helper function to emulate POST requests responses from the web"""

        class MockResponse:
            def __init__(self, data, status_code):
                self.status_code = status_code
                self.content = json.dumps(data)
                self.headers = {"content-encoding": "test", "connection": "fake"}

        if kwargs["url"] == "https://api.github.com/repos/no_existing_pr/response/pulls":
            response_data = {"html_url": "great_success"}
            return MockResponse(response_data, 201)

        return MockResponse({"post_url": kwargs["url"]}, 404)

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    @mock.patch("requests.post", side_effect=mocked_requests_post)
    def test_make_pull_request_success(self, mock_get, mock_post):
        """Try making a PR - successful response"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.gh_username = "no_existing_pr"
        psync.gh_repo = "no_existing_pr/response"
        os.environ["GITHUB_AUTH_TOKEN"] = "test"
        psync.make_pull_request()
        assert psync.gh_pr_returned_data["html_url"] == "great_success"

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    @mock.patch("requests.post", side_effect=mocked_requests_post)
    def test_make_pull_request_bad_response(self, mock_get, mock_post):
        """Try making a PR and getting a 404 error"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.gh_username = "bad_url"
        psync.gh_repo = "bad_url/response"
        os.environ["GITHUB_AUTH_TOKEN"] = "test"
        try:
            psync.make_pull_request()
            raise UserWarning("Should have hit an exception")
        except nf_core.sync.PullRequestException as e:
            assert e.args[0].startswith("GitHub API returned code 404:")
