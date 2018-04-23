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
    wfs.compare_remote_local()

