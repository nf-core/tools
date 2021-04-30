#!/usr/bin/env python
"""Tests for the download subcommand of nf-core tools
"""

import nf_core.create
import nf_core.utils
from nf_core.download import DownloadWorkflow

import hashlib
import mock
import os
import pytest
import shutil
import tempfile
import unittest


class DownloadTest(unittest.TestCase):

    #
    # Tests for 'fetch_workflow_details()'
    #
    def test_fetch_workflow_details_for_nf_core(self):
        download_obj = DownloadWorkflow(pipeline="methylseq")
        download_obj.fetch_workflow_details()
        assert download_obj.wf_name == "nf-core/methylseq"
        for r in download_obj.wf_releases:
            if r.get("tag_name") == "1.6":
                break
        else:
            raise AssertionError("Release 1.6 not found")
        assert "dev" in download_obj.wf_branches.keys()

    def test_fetch_workflow_details_for_not_nf_core(self):
        download_obj = DownloadWorkflow(pipeline="ewels/MultiQC")
        download_obj.fetch_workflow_details()
        assert download_obj.wf_name == "ewels/MultiQC"
        for r in download_obj.wf_releases:
            if r.get("tag_name") == "v1.10":
                break
        else:
            raise AssertionError("MultiQC release v1.10 not found")
        assert "master" in download_obj.wf_branches.keys()

    @pytest.mark.xfail(raises=LookupError, strict=True)
    def test_fetch_workflow_details_not_exists(self):
        download_obj = DownloadWorkflow(pipeline="made_up_pipeline")
        download_obj.fetch_workflow_details()

    @pytest.mark.xfail(raises=LookupError, strict=True)
    def test_fetch_workflow_details_not_exists_slash(self):
        download_obj = DownloadWorkflow(pipeline="made-up/pipeline")
        download_obj.fetch_workflow_details()

    #
    # Tests for 'download_wf_files'
    #
    def test_download_wf_files(self):
        download_obj = DownloadWorkflow(pipeline="dummy", release="1.2.0", outdir=tempfile.mkdtemp())
        download_obj.wf_name = "nf-core/methylseq"
        download_obj.wf_sha = "1.0"
        download_obj.wf_download_url = "https://github.com/nf-core/methylseq/archive/1.0.zip"
        download_obj.download_wf_files()

    #
    # Tests for 'download_configs'
    #
    def test_download_configs(self):
        download_obj = DownloadWorkflow(pipeline="dummy", release="1.2.0", outdir=tempfile.mkdtemp())
        download_obj.download_configs()

    #
    # Tests for 'wf_use_local_configs'
    #
    def test_wf_use_local_configs(self):
        # Get a workflow and configs
        test_pipeline_dir = os.path.join(tempfile.mkdtemp(), "nf-core-testpipeline")
        create_obj = nf_core.create.PipelineCreate(
            "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=test_pipeline_dir
        )
        create_obj.init_pipeline()

        test_outdir = tempfile.mkdtemp()
        download_obj = DownloadWorkflow(pipeline="dummy", release="1.2.0", outdir=test_outdir)
        shutil.copytree(test_pipeline_dir, os.path.join(test_outdir, "workflow"))
        download_obj.download_configs()

        # Test the function
        download_obj.wf_use_local_configs()
        wf_config = nf_core.utils.fetch_wf_config(os.path.join(test_outdir, "workflow"))
        assert wf_config["params.custom_config_base"] == "'../configs/'"

    #
    # Tests for 'find_container_images'
    #
    @mock.patch("nf_core.utils.fetch_wf_config")
    def test_find_container_images(self, mock_fetch_wf_config):
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tempfile.mkdtemp())
        mock_fetch_wf_config.return_value = {
            "process.mapping.container": "cutting-edge-container",
            "process.nocontainer": "not-so-cutting-edge",
        }
        download_obj.find_container_images()
        assert len(download_obj.containers) == 1
        assert download_obj.containers[0] == "cutting-edge-container"

    #
    # Tests for 'validate_md5'
    #
    def test_matching_md5sums(self):
        download_obj = DownloadWorkflow(pipeline="dummy")
        test_hash = hashlib.md5()
        test_hash.update(b"test")
        val_hash = test_hash.hexdigest()
        tmpfilehandle, tmpfile = tempfile.mkstemp()

        with open(tmpfile[1], "w") as f:
            f.write("test")

        download_obj.validate_md5(tmpfile[1], val_hash)

        # Clean up
        os.remove(tmpfile[1])

    @pytest.mark.xfail(raises=IOError, strict=True)
    def test_mismatching_md5sums(self):
        download_obj = DownloadWorkflow(pipeline="dummy")
        test_hash = hashlib.md5()
        test_hash.update(b"other value")
        val_hash = test_hash.hexdigest()
        tmpfilehandle, tmpfile = tempfile.mkstemp()

        with open(tmpfile, "w") as f:
            f.write("test")

        download_obj.validate_md5(tmpfile[1], val_hash)

        # Clean up
        os.remove(tmpfile)

    #
    # Tests for 'singularity_pull_image'
    #
    # If Singularity is not installed, will log an error and exit
    # If Singularity is installed, should raise an OSError due to non-existant image
    @pytest.mark.xfail(raises=OSError)
    @mock.patch("rich.progress.Progress.add_task")
    def test_singularity_pull_image(self, mock_rich_progress):
        tmp_dir = tempfile.mkdtemp()
        download_obj = DownloadWorkflow(pipeline="dummy", outdir=tmp_dir)
        download_obj.singularity_pull_image("a-container", tmp_dir, None, mock_rich_progress)

        # Clean up
        shutil.rmtree(tmp_dir)

    #
    # Tests for the main entry method 'download_workflow'
    #
    @mock.patch("nf_core.download.DownloadWorkflow.singularity_pull_image")
    @mock.patch("shutil.which")
    def test_download_workflow_with_success(self, mock_download_image, mock_singularity_installed):

        tmp_dir = tempfile.mkdtemp()

        download_obj = DownloadWorkflow(
            pipeline="nf-core/methylseq",
            outdir=os.path.join(tmp_dir, "new"),
            container="singularity",
            release="1.6",
            compress_type="none",
        )

        download_obj.download_workflow()

        # Clean up
        shutil.rmtree(tmp_dir)
