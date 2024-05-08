"""Tests covering the sync command"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import git
import pytest

import nf_core.create
import nf_core.sync

from .utils import with_temporary_folder


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        """Create a new pipeline to test"""
        self.tmp_dir = tempfile.mkdtemp()
        self.pipeline_dir = os.path.join(self.tmp_dir, "testpipeline")
        default_branch = "master"
        self.create_obj = nf_core.create.PipelineCreate(
            "testing",
            "test pipeline",
            "tester",
            outdir=self.pipeline_dir,
            plain=True,
            default_branch=default_branch,
        )
        self.create_obj.init_pipeline()
        self.remote_path = os.path.join(self.tmp_dir, "remote_repo")
        self.remote_repo = git.Repo.init(self.remote_path, bare=True)

        if self.remote_repo.active_branch.name != "master":
            self.remote_repo.active_branch.rename(default_branch)

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    @with_temporary_folder
    def test_inspect_sync_dir_notgit(self, tmp_dir):
        """Try syncing an empty directory"""
        psync = nf_core.sync.PipelineSync(tmp_dir)
        with pytest.raises(nf_core.sync.SyncExceptionError) as exc_info:
            psync.inspect_sync_dir()
        assert "does not appear to be a git repository" in exc_info.value.args[0]

    def test_inspect_sync_dir_dirty(self):
        """Try syncing a pipeline with uncommitted changes"""
        # Add an empty file, uncommitted
        test_fn = Path(self.pipeline_dir) / "uncommitted"
        test_fn.touch()
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        try:
            with pytest.raises(nf_core.sync.SyncExceptionError) as exc_info:
                psync.inspect_sync_dir()
            assert exc_info.value.args[0].startswith("Uncommitted changes found in pipeline directory!")
        finally:
            os.remove(test_fn)

    def test_get_wf_config_no_branch(self):
        """Try getting a workflow config when the branch doesn't exist"""
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir, from_branch="foo")
        with pytest.raises(nf_core.sync.SyncExceptionError) as exc_info:
            psync.inspect_sync_dir()
            psync.get_wf_config()
        assert exc_info.value.args[0] == "Branch `foo` not found!"

    def test_get_wf_config_missing_required_config(self):
        """Try getting a workflow config, then make it miss a required config option"""
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.required_config_vars = ["fakethisdoesnotexist"]
        with pytest.raises(nf_core.sync.SyncExceptionError) as exc_info:
            psync.inspect_sync_dir()
            psync.get_wf_config()
        # Check that we did actually get some config back
        assert psync.wf_config["params.validate_params"] == "true"
        # Check that we raised because of the missing fake config var
        assert exc_info.value.args[0] == "Workflow config variable `fakethisdoesnotexist` not found!"

    def test_checkout_template_branch(self):
        """Try checking out the TEMPLATE branch of the pipeline"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()

    def test_checkout_template_branch_no_template(self):
        """Try checking out the TEMPLATE branch of the pipeline when it does not exist"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()

        psync.repo.delete_head("TEMPLATE")

        with pytest.raises(nf_core.sync.SyncExceptionError) as exc_info:
            psync.checkout_template_branch()
        assert exc_info.value.args[0] == "Could not check out branch 'origin/TEMPLATE' or 'TEMPLATE'"

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
        test_fn = Path(self.pipeline_dir) / "uncommitted"
        test_fn.touch()
        # Check that we have uncommitted changes
        assert psync.repo.is_dirty(untracked_files=True) is True
        # Function returns True if no changes were made
        assert psync.commit_template_changes() is True
        # Check that we don't have any uncommitted changes
        assert psync.repo.is_dirty(untracked_files=True) is False

    def test_push_template_branch_error(self):
        """Try pushing the changes, but without a remote (should fail)"""
        # Check out the TEMPLATE branch but skip making the new template etc.
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.checkout_template_branch()
        # Add an empty file and commit it
        test_fn = Path(self.pipeline_dir) / "uncommitted"
        test_fn.touch()
        psync.commit_template_changes()
        # Try to push changes
        with pytest.raises(nf_core.sync.PullRequestExceptionError) as exc_info:
            psync.push_template_branch()
        assert exc_info.value.args[0].startswith("Could not push TEMPLATE branch")

    def test_create_merge_base_branch(self):
        """Try creating a merge base branch"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()

        psync.create_merge_base_branch()

        assert psync.merge_branch in psync.repo.branches

    def test_create_merge_base_branch_thrice(self):
        """Try creating a merge base branch thrice

        This is needed because the first time this function is called, the
        merge branch does not exist yet (it is only created at the end of the
        create_merge_base_branch function) and the if-statement is ignored.
        Also, the second time this function is called, the existing merge
        branch only has the base format, i.e. without the -{branch_no} at the
        end, so it is needed to call it a third time to make sure this is
        picked up.
        """
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()

        for _ in range(3):
            psync.create_merge_base_branch()

        assert psync.merge_branch in psync.repo.branches
        for branch_no in [2, 3]:
            assert f"{psync.original_merge_branch}-{branch_no}" in psync.repo.branches

    def test_push_merge_branch(self):
        """Try pushing merge branch"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.repo.create_remote("origin", self.remote_path)

        psync.create_merge_base_branch()
        psync.push_merge_branch()

        assert psync.merge_branch in [b.name for b in self.remote_repo.branches]

    def test_push_merge_branch_without_create_branch(self):
        """Try pushing merge branch without creating first"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.repo.create_remote("origin", self.remote_path)

        with pytest.raises(nf_core.sync.PullRequestExceptionError) as exc_info:
            psync.push_merge_branch()
        assert exc_info.value.args[0].startswith(f"Could not push branch '{psync.merge_branch}'")

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

        url_template = "https://api.github.com/repos/{}/response/"
        if url == os.path.join(url_template.format("no_existing_pr"), "pulls?head=TEMPLATE&base=None"):
            response_data = []
            return MockResponse(response_data, 200)
        if url == os.path.join(url_template.format("list_prs"), "pulls"):
            response_data = [
                {
                    "state": "closed",
                    "head": {"ref": "nf-core-template-merge-2"},
                    "base": {"ref": "master"},
                    "html_url": "pr_url",
                }
            ] + [
                {
                    "state": "open",
                    "head": {"ref": f"nf-core-template-merge-{branch_no}"},
                    "base": {"ref": "master"},
                    "html_url": "pr_url",
                }
                for branch_no in range(3, 7)
            ]
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
        with pytest.raises(nf_core.sync.PullRequestExceptionError) as exc_info:
            psync.make_pull_request()
        assert exc_info.value.args[0].startswith(
            "Something went badly wrong - GitHub API PR failed - got return code 404"
        )

    @mock.patch("nf_core.utils.gh_api.get", side_effect=mocked_requests_get)
    def test_close_open_template_merge_prs(self, mock_get):
        """Try closing all open prs"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.gh_api.get = mock_get
        psync.gh_username = "list_prs"
        psync.gh_repo = "list_prs/response"
        os.environ["GITHUB_AUTH_TOKEN"] = "test"

        with mock.patch("nf_core.sync.PipelineSync.close_open_pr") as mock_close_open_pr:
            psync.close_open_template_merge_prs()

            prs = mock_get(f"https://api.github.com/repos/{psync.gh_repo}/pulls").data
            for pr in prs:
                if pr["state"] == "open":
                    mock_close_open_pr.assert_any_call(pr)

    @mock.patch("nf_core.utils.gh_api.post", side_effect=mocked_requests_post)
    @mock.patch("nf_core.utils.gh_api.patch", side_effect=mocked_requests_patch)
    def test_close_open_pr(self, mock_patch, mock_post):
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.gh_api.post = mock_post
        psync.gh_api.patch = mock_patch
        psync.gh_username = "bad_url"
        psync.gh_repo = "bad_url/response"
        os.environ["GITHUB_AUTH_TOKEN"] = "test"
        pr = {
            "state": "open",
            "head": {"ref": "nf-core-template-merge-3"},
            "base": {"ref": "master"},
            "html_url": "pr_html_url",
            "url": "url_to_update_pr",
            "comments_url": "pr_comments_url",
        }

        assert psync.close_open_pr(pr)
        mock_patch.assert_called_once_with(url="url_to_update_pr", data='{"state": "closed"}')

    @mock.patch("nf_core.utils.gh_api.post", side_effect=mocked_requests_post)
    @mock.patch("nf_core.utils.gh_api.patch", side_effect=mocked_requests_patch)
    def test_close_open_pr_fail(self, mock_patch, mock_post):
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()
        psync.gh_api.post = mock_post
        psync.gh_api.patch = mock_patch
        psync.gh_username = "bad_url"
        psync.gh_repo = "bad_url/response"
        os.environ["GITHUB_AUTH_TOKEN"] = "test"
        pr = {
            "state": "open",
            "head": {"ref": "nf-core-template-merge-3"},
            "base": {"ref": "master"},
            "html_url": "pr_html_url",
            "url": "bad_url_to_update_pr",
            "comments_url": "pr_comments_url",
        }

        assert not psync.close_open_pr(pr)
        mock_patch.assert_called_once_with(url="bad_url_to_update_pr", data='{"state": "closed"}')

    def test_reset_target_dir(self):
        """Try resetting target pipeline directory"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()

        psync.repo.git.checkout("dev")

        psync.reset_target_dir()

        assert psync.repo.heads[0].name == "TEMPLATE"

    def test_reset_target_dir_fake_branch(self):
        """Try resetting target pipeline directory but original branch does not exist"""
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        psync.get_wf_config()

        psync.original_branch = "fake_branch"

        with pytest.raises(nf_core.sync.SyncExceptionError) as exc_info:
            psync.reset_target_dir()
        assert exc_info.value.args[0].startswith("Could not reset to original branch `fake_branch`")
