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

@pytest.fixture(scope="class")
def example_json():
    assert os.path.isfile(PATH_WORKING_EXAMPLE)
    with open(PATH_WORKING_EXAMPLE) as fp:
        content = fp.read()
    return content

def test_creating_params_from_json(example_json):
    """Tests parsing of a parameter json."""
    result = pms.Parameters.create_from_json(example_json)
    assert len(result) == 2

def test_params_as_json_dump(example_json):
    """Tests the JSON dump that can be consumed by Nextflow."""
    result = pms.Parameters.create_from_json(example_json)
    parameter = result[0]
    assert parameter.name == "reads"
    expected_output = """
    {
        "reads": "path/to/reads.fastq.gz"
    }"""
    parsed_output = json.loads(expected_output)
    assert len(parsed_output.keys()) == 1
    assert parameter.name in parsed_output.keys()
    assert parameter.default_value == parsed_output[parameter.name]
