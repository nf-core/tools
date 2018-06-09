#!/usr/bin/env python
"""Tests for the download subcommand of nf-core tools
"""

import nf_core.list
from nf_core.download import DownloadWorkflow

import mock
import pytest
import unittest

class DownloadTest(unittest.TestCase):

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
    def test_fetch_workflow_details_for_unknown_workflow(self, mock_workflows):
        download_obj = DownloadWorkflow(
            pipeline = "myorg/dummy",
            release = "1.2.0"
            )
        mock_workflows.remote_workflows = []

        download_obj.fetch_workflow_details(mock_workflows)

    @mock.patch('nf_core.list.Workflows')
    @pytest.mark.xfail(raises=LookupError)
    def test_fetch_workflow_details_no_search_result(self, mock_workflows):
        download_obj = DownloadWorkflow(
            pipeline = "http://my-server.org/dummy",
            release = "1.2.0"
            )
        mock_workflows.remote_workflows = []

        download_obj.fetch_workflow_details(mock_workflows)

        
