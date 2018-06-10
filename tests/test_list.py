#!/usr/bin/env python
""" Tests covering the workflow listing code.
"""
import os
import time
import pytest
import unittest
import nf_core.list
from nose.tools import raises
from datetime import datetime

class TestLint(unittest.TestCase):
    """Class for list tests"""

    def test_working_listcall(self):
        """ Test that listing pipelines works """
        nf_core.list.list_workflows()

    def test_working_listcall_json(self):
        """ Test that listing pipelines with JSON works """
        nf_core.list.list_workflows(True)

    def test_pretty_datetime(self):
        """ Test that the pretty datetime function works """
        now = datetime.now()
        nf_core.list.pretty_date(now)
        now_ts = time.mktime(now.timetuple())
        nf_core.list.pretty_date(now_ts)

    @raises(AssertionError)
    def test_local_workflows_and_fail(self):
        """ Test the local workflow class and try to get local
        Nextflow workflow information """
        loc_wf = nf_core.list.LocalWorkflow("myWF")
        loc_wf.get_local_nf_workflow_details()

    def test_local_workflows_compare_and_fail_silently(self):
        """ Test the workflow class and try to compare local
        and remote workflows """
        wfs = nf_core.list.Workflows()
        lwf_ex = nf_core.list.LocalWorkflow("myWF")
        lwf_ex.full_name = 'my Workflow'
        lwf_ex.commit_sha = "aw3s0meh1sh"

        remote = {
            'name': 'myWF',
            'full_name': 'my Workflow',
            'description': '...',
            'archived': [],
            'stargazers_count': 42,
            'watchers_count': 6,
            'forks_count': 7,
            'releases': []
        }

        rwf_ex = nf_core.list.RemoteWorkflow(remote)
        rwf_ex.commit_sha = "aw3s0meh1sh"
        rwf_ex.releases = [{'tag_sha': "aw3s0meh1sh"}]
    

        wfs.local_workflows.append(lwf_ex)
        wfs.remote_workflows.append(rwf_ex)
        wfs.compare_remote_local()

        self.assertEqual(rwf_ex.local_wf, lwf_ex)

        rwf_ex.releases = []
        rwf_ex.releases.append({'tag_sha': "noaw3s0meh1sh"})
        wfs.compare_remote_local()

        rwf_ex.full_name = "your Workflow"
        wfs.compare_remote_local()

        rwf_ex.releases = None