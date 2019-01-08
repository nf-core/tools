#!/usr/bin/env python
"""Some tests covering the parameters code.
"""
import json
import os
import pytest
import shutil
import unittest
import nf_core.workflow.parameters as pms

WD = os.path.dirname(__file__)
PATH_WORKING_EXAMPLE = os.path.join(WD, 'example.json')

def test_creating_params_from_json():
    """Tests parsing of a parameter json."""
    assert os.path.isfile(PATH_WORKING_EXAMPLE)
    with open(PATH_WORKING_EXAMPLE) as fp:
        result = pms.Parameters.create_from_json(fp.read())
    assert len(result) == 2