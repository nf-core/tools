#!/usr/bin/env python
"""Tests for the download subcommand of nf-core tools
"""

import nf_core.list
from nf_core.download import DownloadWorkflow

import hashlib
import io
import mock
import os
import pytest
import requests
import shutil
import tempfile
import unittest

class DownloadTest(unittest.TestCase):

    #
    # Tests for 'fetch_workflow_details()'
    #
    @mock.patch('nf_core.list.RemoteWorkflow')
    @mock.patch('nf_core.list.Workflows')
    def test_fetch_workflow_details_for_release(self, mock_workflows, mock_workflow):
        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            release="1.0.0"
            )
        mock_workflow.name = "dummy"
        mock_workflow.releases = [{"tag_name": "1.0.0", "tag_sha": "n3v3rl4nd"}]
        mock_workflows.remote_workflows = [mock_workflow]

        download_obj.fetch_workflow_details(mock_workflows)

    @mock.patch('nf_core.list.RemoteWorkflow')
    @mock.patch('nf_core.list.Workflows')
    def test_fetch_workflow_details_for_dev_version(self, mock_workflows, mock_workflow):
        download_obj = DownloadWorkflow(pipeline = "dummy")
        mock_workflow.name = "dummy"
        mock_workflow.releases = []
        mock_workflows.remote_workflows = [mock_workflow]

        download_obj.fetch_workflow_details(mock_workflows)

    @mock.patch('nf_core.list.RemoteWorkflow')
    @mock.patch('nf_core.list.Workflows')
    def test_fetch_workflow_details_and_autoset_release(self, mock_workflows, mock_workflow):
        download_obj = DownloadWorkflow(pipeline = "dummy")
        mock_workflow.name = "dummy"
        mock_workflow.releases = [{"tag_name": "1.0.0", "tag_sha": "n3v3rl4nd"}]
        mock_workflows.remote_workflows = [mock_workflow]

        download_obj.fetch_workflow_details(mock_workflows)
        assert download_obj.release == "1.0.0"

    @mock.patch('nf_core.list.RemoteWorkflow')
    @mock.patch('nf_core.list.Workflows')
    @pytest.mark.xfail(raises=LookupError)
    def test_fetch_workflow_details_for_unknown_release(self, mock_workflows, mock_workflow):
        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            release = "1.2.0"
            )
        mock_workflow.name = "dummy"
        mock_workflow.releases = [{"tag_name": "1.0.0", "tag_sha": "n3v3rl4nd"}]
        mock_workflows.remote_workflows = [mock_workflow]

        download_obj.fetch_workflow_details(mock_workflows)

    @mock.patch('nf_core.list.Workflows')
    def test_fetch_workflow_details_for_github_ressource(self, mock_workflows):
        download_obj = DownloadWorkflow(
            pipeline = "myorg/dummy",
            release = "1.2.0"
            )
        mock_workflows.remote_workflows = []

        download_obj.fetch_workflow_details(mock_workflows)

    @mock.patch('nf_core.list.Workflows')
    def test_fetch_workflow_details_for_github_ressource_take_master(self, mock_workflows):
        download_obj = DownloadWorkflow(
            pipeline = "myorg/dummy"
            )
        mock_workflows.remote_workflows = []

        download_obj.fetch_workflow_details(mock_workflows)
        assert download_obj.release == "master"

    @mock.patch('nf_core.list.Workflows')
    @pytest.mark.xfail(raises=LookupError)
    def test_fetch_workflow_details_no_search_result(self, mock_workflows):
        download_obj = DownloadWorkflow(
            pipeline = "http://my-server.org/dummy",
            release = "1.2.0"
            )
        mock_workflows.remote_workflows = []

        download_obj.fetch_workflow_details(mock_workflows)

    #
    # Tests for 'download_wf_files'
    #
    def test_download_wf_files(self):
        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            release = "1.2.0",
            outdir = tempfile.mkdtemp()
            )
        download_obj.wf_name = "nf-core/methylseq"
        download_obj.wf_sha = "1.0"
        download_obj.wf_download_url = "https://github.com/nf-core/methylseq/archive/1.0.zip"
        download_obj.download_wf_files()

    #
    # Tests for 'find_singularity_images'
    #
    @mock.patch('nf_core.utils.fetch_wf_config')
    def test_find_singularity_images(self, mock_fetch_wf_config):
        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            outdir = tempfile.mkdtemp())
        mock_fetch_wf_config.return_value = {
            'process.mapping.container': 'cutting-edge-container',
            'process.nocontainer': 'not-so-cutting-edge'
        }
        download_obj.find_singularity_images()
        assert len(download_obj.containers) == 1
        assert download_obj.containers[0] == 'cutting-edge-container'

    #
    # Tests for 'download_shub_image'
    #
    @mock.patch('nf_core.download.DownloadWorkflow.validate_md5')
    @mock.patch('click.progressbar')
    @mock.patch('requests.Response.iter_content')
    @mock.patch('requests.Response.json')
    @mock.patch('requests.get')
    def test_download_shub_image_on_sucess(self,
        mock_request,
        mock_json,
        mock_content,
        mock_progressbar,
        mock_md5):

        tmp_dir = tempfile.mkdtemp()
        os.mkdir(os.path.join(tmp_dir, 'singularity-images'))

        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            outdir = tmp_dir)

        # simulauates the first response querying the API for the container
        # information
        resp_shub = requests.Response()
        resp_shub.status_code = 200
        mock_json.side_effect = [{'image': 'my-container', 'version': 'h4sh'}]

        # simulates the second response querying the
        # container download stream
        resp_download = requests.Response()
        resp_download.status_code = 200
        resp_download.headers = {'content-length' : 1024}
        mock_content.side_effect = b"Awesome"

        # assign the response order
        mock_request.side_effect = [resp_shub, resp_download]
        # test
        download_obj.download_shub_image("awesome-container")

        # Clean up
        shutil.rmtree(tmp_dir)

    @mock.patch('requests.get')
    @pytest.mark.xfail(raises=RuntimeWarning)
    def test_download_image_shub_without_hit(self,
        mock_request):

        # we need this for the fake download
        tmp_dir = "/tmp/singularity-images"
        if not os.path.isdir(tmp_dir): os.mkdir(tmp_dir)

        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            outdir = tempfile.mkdtemp())

        # simulauates the first response querying the API for the container
        # information
        resp_shub = requests.Response()
        resp_shub.status_code = 404

        # assign the response order
        mock_request.side_effect = [resp_shub]

        # test
        download_obj.download_shub_image("awesome-container")

        # Clean up
        shutil.rmtree(tmp_dir)

    @mock.patch('requests.Response.json')
    @mock.patch('requests.get')
    @pytest.mark.xfail(raises=RuntimeWarning)
    def test_download_image_shub_wrong_url(self,
        mock_request,
        mock_json):

        # we need this for the fake download
        tmp_dir = "/tmp/singularity-images"
        if not os.path.isdir(tmp_dir): os.mkdir(tmp_dir)

        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            outdir = tempfile.mkdtemp())

        # simulauates the first response querying the API for the container
        # information
        resp_shub = requests.Response()
        resp_shub.status_code = 200
        mock_json.side_effect = [{'image': 'my-container', 'version': 'h4sh'}]

         # simulates the second response querying the
        # container download stream
        resp_download = requests.Response()
        resp_download.status_code = 404

        # assign the response order
        mock_request.side_effect = [resp_shub, resp_download]

        # test
        download_obj.download_shub_image("awesome-container")

        # Clean up
        shutil.rmtree(tmp_dir)

    @mock.patch('requests.Response.json')
    @mock.patch('requests.get')
    @pytest.mark.xfail(raises=ImportError)
    def test_download_image_shub_unknown_response(self,
        mock_request,
        mock_json):

        # we need this for the fake download
        tmp_dir = "/tmp/singularity-images"
        if not os.path.isdir(tmp_dir): os.mkdir(tmp_dir)

        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            outdir = tempfile.mkdtemp())

        # simulauates the first response querying the API for the container
        # information
        resp_shub = requests.Response()
        resp_shub.status_code = 301
        mock_json.side_effect = [{'image': 'my-container', 'version': 'h4sh'}]

        # assign the response order
        mock_request.side_effect = [resp_shub]

        # test
        download_obj.download_shub_image("awesome-container")

        # Clean up
        shutil.rmtree(tmp_dir)

    #
    # Tests for 'validate_md5'
    #
    def test_matching_md5sums(self):
        download_obj = DownloadWorkflow(pipeline = "dummy")
        test_hash = hashlib.md5()
        test_hash.update(b"test")
        val_hash = test_hash.hexdigest()
        tmpfilehandle, tmpfile = tempfile.mkstemp()

        with open(tmpfile[1], "w") as f: f.write("test")

        download_obj.validate_md5(tmpfile[1], val_hash)

        # Clean up
        shutil.rmtree(tmpfile)

    @pytest.mark.xfail(raises=IOError)
    def test_mismatching_md5sums(self):
        download_obj = DownloadWorkflow(pipeline = "dummy")
        test_hash = hashlib.md5()
        test_hash.update(b"other value")
        val_hash = test_hash.hexdigest()
        tmpfilehandle, tmpfile = tempfile.mkstemp()

        with open(tmpfile, "w") as f: f.write("test")

        download_obj.validate_md5(tmpfile[1], val_hash)

        # Clean up
        shutil.rmtree(tmpfile)

    #
    # Tests for 'pull_singularity_image'
    #
    @pytest.mark.xfail(raises=OSError)
    def test_pull_singularity_image(self):
        tmp_dir = tempfile.mkdtemp()
        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            outdir = tmp_dir)
        download_obj.pull_singularity_image("a-container")

        # Clean up
        shutil.rmtree(tmp_dir)

    #
    # Tests for the main entry method 'download_workflow'
    #
    @mock.patch('nf_core.download.DownloadWorkflow.pull_singularity_image')
    @mock.patch('nf_core.download.DownloadWorkflow.download_shub_image')
    def test_download_workflow_with_success(self,
        mock_download_shub,
        mock_download_image):

        tmp_dir = os.path.join(tempfile.mkdtemp(), 'new')

        download_obj = DownloadWorkflow(
            pipeline = "nf-core/methylseq",
            outdir = tmp_dir,
            singularity = True)

        mock_download_shub.side_effect = RuntimeWarning()

        download_obj.download_workflow()

        # Clean up
        shutil.rmtree(tmp_dir)
