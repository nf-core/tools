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
    # Tests for 'get_release_hash'
    #
    def test_get_release_hash_release(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline = "methylseq"
        download_obj = DownloadWorkflow(pipeline=pipeline, release="1.6")
        (
            download_obj.pipeline,
            download_obj.wf_releases,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        download_obj.get_revisions_hash()
        assert download_obj.wf_sha == "b3e5e3b95aaf01d98391a62a10a3990c0a4de395"
        assert download_obj.outdir == "nf-core-methylseq-1.6"
        assert (
            download_obj.wf_download_url
            == "https://github.com/nf-core/methylseq/archive/b3e5e3b95aaf01d98391a62a10a3990c0a4de395.zip"
        )

    def test_get_release_hash_branch(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        # Exoseq pipeline is archived, so `dev` branch should be stable
        pipeline = "exoseq"
        download_obj = DownloadWorkflow(pipeline=pipeline, release="dev")
        (
            download_obj.pipeline,
            download_obj.wf_releases,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        download_obj.get_revisions_hash()
        assert download_obj.wf_sha == "819cbac792b76cf66c840b567ed0ee9a2f620db7"
        assert download_obj.outdir == "nf-core-exoseq-dev"
        assert (
            download_obj.wf_download_url
            == "https://github.com/nf-core/exoseq/archive/819cbac792b76cf66c840b567ed0ee9a2f620db7.zip"
        )

    @pytest.mark.xfail(raises=AssertionError, strict=True)
    def test_get_release_hash_non_existent_release(self):
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()
        pipeline = "methylseq"
        download_obj = DownloadWorkflow(pipeline=pipeline, release="thisisfake")
        (
            download_obj.pipeline,
            download_obj.wf_releases,
            download_obj.wf_branches,
        ) = nf_core.utils.get_repo_releases_branches(pipeline, wfs)
        download_obj.get_revisions_hash()

    #
    # Tests for 'download_wf_files'
    #
    def test_download_wf_files(self):
        outdir = tempfile.mkdtemp()
        download_obj = DownloadWorkflow(pipeline="nf-core/methylseq", release="1.6")
        download_obj.outdir = outdir
        download_obj.wf_sha = "b3e5e3b95aaf01d98391a62a10a3990c0a4de395"
        download_obj.wf_download_url = (
            "https://github.com/nf-core/methylseq/archive/b3e5e3b95aaf01d98391a62a10a3990c0a4de395.zip"
        )
        download_obj.download_wf_files()
        assert os.path.exists(os.path.join(outdir, "workflow", "main.nf"))

    #
    # Tests for 'download_configs'
    #
    def test_download_configs(self):
        outdir = tempfile.mkdtemp()
        download_obj = DownloadWorkflow(pipeline="nf-core/methylseq", release="1.6")
        download_obj.outdir = outdir
        download_obj.download_configs()
        assert os.path.exists(os.path.join(outdir, "configs", "nfcore_custom.config"))

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
        assert wf_config["params.custom_config_base"] == f"'{test_outdir}/workflow/../configs/'"

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
        os.environ["NXF_SINGULARITY_CACHEDIR"] = "foo"

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
