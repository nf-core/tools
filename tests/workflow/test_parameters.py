#!/usr/bin/env python
"""Some tests covering the parameters code.
"""
import json
import jsonschema
from jsonschema import ValidationError
import os
import pytest
import requests
import shutil
import unittest
from nf_core.workflow import parameters as pms

WD = os.path.dirname(__file__)
PATH_WORKING_EXAMPLE = os.path.join(WD, 'example.json')
SCHEMA_URI = "https://nf-co.re/parameters.schema.json"

@pytest.fixture(scope="class")
def schema():
    res = requests.get(SCHEMA_URI)
    assert res.status_code == 200
    return res.text

@pytest.fixture(scope="class")
def example_json():
    assert os.path.isfile(PATH_WORKING_EXAMPLE)
    with open(PATH_WORKING_EXAMPLE) as fp:
        content = fp.read()
    return content

def test_creating_params_from_json(example_json):
    """Tests parsing of a parameter json."""
    result = pms.Parameters.create_from_json(example_json)
    assert len(result) == 3

def test_groups_from_json(example_json):
    """Tests group property of a parameter json."""
    result = pms.Parameters.create_from_json(example_json)
    group_labels = set([ param.group for param in result ])
    assert len(group_labels) == 2

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

def test_parameter_builder():
    """Tests the parameter builder."""
    parameter = pms.Parameter.builder().name("width").default(2).build()
    assert parameter.name == "width"
    assert parameter.default_value == 2

@pytest.mark.xfail(raises=ValidationError)
def test_validation(schema):
    """Tests the parameter objects against the JSON schema."""
    parameter = pms.Parameter.builder().name("width").param_type("unknown").default(2).build()
    params_in_json = pms.Parameters.in_full_json([parameter])
    jsonschema.validate(json.loads(pms.Parameters.in_full_json([parameter])), json.loads(schema))

def test_validation_with_success(schema):
    """Tests the parameter objects against the JSON schema."""
    parameter = pms.Parameter.builder().name("width").param_type("integer") \
            .default(2).label("The width of a table.").render("textfield").required(False).build()
    params_in_json = pms.Parameters.in_full_json([parameter])
    jsonschema.validate(json.loads(pms.Parameters.in_full_json([parameter])), json.loads(schema))
