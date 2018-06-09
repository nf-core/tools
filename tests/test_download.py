#!/usr/bin/env python
"""Tests for the download subcommand of nf-core tools
"""

import nf_core.list
from nf_core.download import DownloadWorkflow

import mock
import unittest

class DownloadTest(unittest.TestCase):

    @mock.patch('nf_core.list.RemoteWorkflow')
    @mock.patch('nf_core.list.Workflows')
    def test_fetch_workflow_details_of_release(self, mock_workflows, mock_workflow):
        download_obj = DownloadWorkflow(
            pipeline = "dummy",
            release="1.0.0")
        mock_workflow.name = "dummy"
        mock_workflow.releases = [{"tag_name": "1.0.0", "tag_sha": "n3v3rl4nd"}]
        mock_workflows.remote_workflows = [mock_workflow]
        
        download_obj.fetch_workflow_details(mock_workflows)
        


