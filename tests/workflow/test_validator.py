#!/usr/bin/env python
"""Some tests covering the parameters code.
"""
import os
import pytest
import requests
import shutil
import unittest
import nf_core.workflow.parameters as pms
import nf_core.workflow.validation as valid


WD = os.path.dirname(__file__)
PATH_WORKING_EXAMPLE = os.path.join(WD, 'example.json')
SCHEMA_URI = "https://nf-co.re/parameters.schema.json"

@pytest.fixture(scope="class")
def valid_integer_param():
    param = pms.Parameter.builder().name("Fake Integer Param") \
        .default("0").value("10").choices(["0", "10"]).param_type("integer").build()
    return param

@pytest.fixture(scope="class")
def invalid_integer_param():
    param = pms.Parameter.builder().name("Fake Integer Param") \
        .default("0").value("20").choices(["0", "10"]).param_type("integer").build()
    return param

def test_simple_integer_validation(valid_integer_param):
    validator = valid.Validators.get_validator_for_param(valid_integer_param)
    validator.validate()

@pytest.mark.xfail(raises=AttributeError)
def test_simple_integer_out_of_range(invalid_integer_param):
    validator = valid.Validators.get_validator_for_param(invalid_integer_param)
    validator.validate()