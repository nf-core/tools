#!/usr/bin/env python
""" Tests covering the workflow listing code.
"""
import os
import pytest
import unittest
import nf_core.list

def test_working_listcall():
    """ Test that listing pipelines works """
    nf_core.list.list_workflows()

def test_working_listcall_json():
    """ Test that listing pipelines with JSON works """
    nf_core.list.list_workflows(True)
