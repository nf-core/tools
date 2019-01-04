#!/usr/bin/env python
""" Tests covering the workflow listing code.
"""

import nf_core.list

import mock
import os
import git
import pytest
import time
import unittest

from nose.tools import raises
from datetime import datetime

class TestLint(unittest.TestCase):
    """Class for list tests"""

    @mock.patch('json.dumps')
    @mock.patch('subprocess.check_output')
    @mock.patch('nf_core.list.LocalWorkflow')
    def test_working_listcall(self, mock_loc_wf, mock_subprocess, mock_json):
        """ Test that listing pipelines works """
        nf_core.list.list_workflows()

    @mock.patch('json.dumps')
    @mock.patch('subprocess.check_output')
    @mock.patch('nf_core.list.LocalWorkflow')
    def test_working_listcall_json(self, mock_loc_wf, mock_subprocess, mock_json):
        """ Test that listing pipelines with JSON works """
        nf_core.list.list_workflows([], as_json=True)

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
    
    @mock.patch('nf_core.list.LocalWorkflow')
    def test_parse_local_workflow_and_succeed(self, mock_local_wf):
        test_path = '/tmp/nxf/nf-core'
        if not os.path.isdir(test_path): os.makedirs(test_path)

        if not os.environ.get('NXF_ASSETS'):
            os.environ['NXF_ASSETS'] = '/tmp/nxf'
        assert os.environ['NXF_ASSETS'] == '/tmp/nxf'
        with open('/tmp/nxf/nf-core/dummy-wf', 'w') as f: 
            f.write('dummy')
        workflows_obj = nf_core.list.Workflows()
        workflows_obj.get_local_nf_workflows()
        assert len(workflows_obj.local_workflows) == 1

    @mock.patch('os.environ.get')
    @mock.patch('nf_core.list.LocalWorkflow')
    @mock.patch('subprocess.check_output')
    def test_parse_local_workflow_home(self, mock_subprocess, mock_local_wf, mock_env):
        test_path = '/tmp/nxf/nf-core'
        if not os.path.isdir(test_path): os.makedirs(test_path)

        mock_env.side_effect = '/tmp/nxf'

        assert os.environ['NXF_ASSETS'] == '/tmp/nxf'
        with open('/tmp/nxf/nf-core/dummy-wf', 'w') as f: 
            f.write('dummy')
        workflows_obj = nf_core.list.Workflows()
        workflows_obj.get_local_nf_workflows()
    
    @mock.patch('os.stat')
    @mock.patch('git.Repo')
    def test_local_workflow_investigation(self, mock_repo, mock_stat):
        local_wf = nf_core.list.LocalWorkflow('dummy')
        local_wf.local_path = '/tmp'
        mock_repo.head.commit.hexsha = 'h00r4y'
        mock_stat.st_mode = 1
        local_wf.get_local_nf_workflow_details()
    

    def test_worflow_filter(self):
        workflows_obj = nf_core.list.Workflows(["rna", "myWF"])

        remote = {
            'name': 'myWF',
            'full_name': 'my Workflow',
            'description': 'rna',
            'archived': [],
            'stargazers_count': 42,
            'watchers_count': 6,
            'forks_count': 7,
            'releases': []
        }

        rwf_ex = nf_core.list.RemoteWorkflow(remote)
        rwf_ex.commit_sha = "aw3s0meh1sh"
        rwf_ex.releases = [{'tag_sha': "aw3s0meh1sh"}]

        remote2 = {
            'name': 'myWF',
            'full_name': 'my Workflow',
            'description': 'dna',
            'archived': [],
            'stargazers_count': 42,
            'watchers_count': 6,
            'forks_count': 7,
            'releases': []
        }

        rwf_ex2 = nf_core.list.RemoteWorkflow(remote2)
        rwf_ex2.commit_sha = "aw3s0meh1sh"
        rwf_ex2.releases = [{'tag_sha': "aw3s0meh1sh"}]

        workflows_obj.remote_workflows.append(rwf_ex)
        workflows_obj.remote_workflows.append(rwf_ex2)

        assert len(workflows_obj.filtered_workflows()) == 1
