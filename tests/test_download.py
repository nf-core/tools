#!/usr/bin/env python
"""Tests for the download subcommand of nf-core tools
"""

import nf_core.list
from nf_core.download import DownloadWorkflow

import io
import mock
import pytest
import requests
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
            outdir="/tmp"
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
            outdir = "/tmp")
        mock_fetch_wf_config.return_value = {
            'process.mapping.container': 'cutting-edge-container',
            'process.nocontainer': 'not-so-cutting-edge'
        }
        download_obj.find_singularity_images()
        assert len(download_obj.containers) == 1
        assert download_obj.containers[0] == 'cutting-edge-container'
        