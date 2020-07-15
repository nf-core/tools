#!/usr/bin/env python
""" Tests covering the sync command
"""

import nf_core.create
import nf_core.sync

import mock
import os
import shutil
import tempfile
import unittest


class TestModules(unittest.TestCase):
    """Class for modules tests"""

    def setUp(self):
        self.make_new_pipeline()

    def make_new_pipeline(self):
        """ Create a new pipeline to test """
        self.pipeline_dir = os.path.join(tempfile.mkdtemp(), "test_pipeline")
        self.create_obj = nf_core.create.PipelineCreate("testing", "test pipeline", "tester", outdir=self.pipeline_dir)
        self.create_obj.init_pipeline()

    def test_inspect_sync_dir_notgit(self):
        """ Try syncing an empty directory """
        psync = nf_core.sync.PipelineSync(tempfile.mkdtemp())
        try:
            psync.inspect_sync_dir()
        except nf_core.sync.SyncException as e:
            assert "does not appear to be a git repository" in e.args[0]

    def test_inspect_sync_dir_dirty(self):
        """ Try syncing a pipeline with uncommitted changes """
        # Add an empty file, uncommitted
        test_fn = os.path.join(self.pipeline_dir, "uncommitted")
        open(test_fn, "a").close()
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        try:
            psync.inspect_sync_dir()
        except nf_core.sync.SyncException as e:
            os.remove(test_fn)
            assert e.args[0].startswith("Uncommitted changes found in pipeline directory!")
        except Exception as e:
            os.remove(test_fn)
            raise e

    def test_get_wf_config_no_branch(self):
        """ Try getting a workflow config when the branch doesn't exist """
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir, from_branch="foo")
        try:
            psync.inspect_sync_dir()
            psync.get_wf_config()
        except nf_core.sync.SyncException as e:
            assert e.args[0] == "Branch `foo` not found!"

    def test_get_wf_config_fetch_origin(self):
        """
        Try getting the GitHub username and repo from the git origin

        Also checks the fetched config variables, should pass
        """
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.inspect_sync_dir()
        # Add a remote to the git repo
        psync.repo.create_remote("origin", "https://github.com/nf-core/demo.git")
        psync.get_wf_config()
        assert psync.gh_username == "nf-core"
        assert psync.gh_repo == "demo"

    def test_get_wf_config_missing_required_config(self):
        """ Try getting a workflow config, then make it miss a required config option """
        # Try to sync, check we halt with the right error
        psync = nf_core.sync.PipelineSync(self.pipeline_dir)
        psync.required_config_vars = ["fakethisdoesnotexist"]
        try:
            psync.inspect_sync_dir()
            psync.get_wf_config()
        except nf_core.sync.SyncException as e:
            # Check that we did actually get some config back
            assert psync.wf_config["params.outdir"] == "'./results'"
            # Check that we raised because of the missing fake config var
            assert e.args[0] == "Workflow config variable `fakethisdoesnotexist` not found!"
