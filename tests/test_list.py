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

def test_working_listcall():
    """ Test that listing pipelines works """
    nf_core.list.list_workflows()

def test_working_listcall_json():
    """ Test that listing pipelines with JSON works """
    nf_core.list.list_workflows(True)

def test_pretty_datetime():
    """ Test that the pretty datetime function works """
    now = datetime.now()
    nf_core.list.pretty_date(now)
    now_ts = time.mktime(now.timetuple())
    nf_core.list.pretty_date(now_ts)

@raises(AssertionError)
def test_local_workflows_and_fail():
    """ Test the local workflow class and try to get local
    Nextflow workflow information """
    loc_wf = nf_core.list.LocalWorkflow("myWF")
    loc_wf.get_local_nf_workflow_details()

def test_local_workflows_compare_and_fail_silently():
    """ Test the workflow class and try to compare local
    and remote workflows """
    wfs = nf_core.list.Workflows()
    lwf_ex = nf_core.list.LocalWorkflow("myWF")
    lwf_ex.commit_sha = "aw3s0meh1sh"

    remote = {
        'name': 'myWF',
        'full_name': 'my Workflow',
        'description': '...',
        'archived': [],
        'stargazers_count': 42,
        'watchers_count': 6,
        'forks_count': 7,
    }

    rwf_ex = nf_core.list.RemoteWorkflow(remote)
    rwf_ex.commit_sha = "aw3s0meh1sh"
    rwf_ex.full_name = 'my Workflow'
    rwf_ex.releases = []
    rwf_ex.releases.append({'tag_sha': "aw3s0meh1sh"})

    wfs.local_workflows.append(lwf_ex)
    wfs.remote_workflows.append(rwf_ex)
    wfs.compare_remote_local()

    rwf_ex.releases = []
    rwf_ex.releases.append({'tag_sha': "noaw3s0meh1sh"})
    wfs.compare_remote_local()

    rwf_ex.releases = None
    wfs.compare_remote_local()

    rwf_ex.full_name = "your Workflow"
    wfs.compare_remote_local()