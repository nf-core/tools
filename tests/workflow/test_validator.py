#!/usr/bin/env python
"""Some tests covering the parameters code.
"""
import os
import pytest
import requests
import shutil
import unittest
from nf_core.workflow import parameters as pms
from nf_core.workflow import validation as valid


WD = os.path.dirname(__file__)
PATH_WORKING_EXAMPLE = os.path.join(WD, 'example.json')
SCHEMA_URI = "https://nf-co.re/parameters.schema.json"

@pytest.fixture(scope="class")
def valid_integer_param():
    param = pms.Parameter.builder().name("Fake Integer Param") \
        .default(0).value(10).choices([0, 10]).param_type("integer").build()
    return param

@pytest.fixture(scope="class")
def invalid_integer_param():
    param = pms.Parameter.builder().name("Fake Integer Param") \
        .default(0).value(20).choices([0, 10]).param_type("integer").build()
    return param

@pytest.fixture(scope="class")
def invalid_string_param_without_pattern_and_choices():
    param = pms.Parameter.builder().name("Fake String Param") \
        .default("Not empty!").value("Whatever").choices(["0", "10"]).param_type("integer").build()
    return param

@pytest.fixture(scope="class")
def param_with_unknown_type():
    param = pms.Parameter.builder().name("Fake String Param") \
        .default("Not empty!").value("Whatever").choices(["0", "10"]).param_type("unknown").build()
    return param

@pytest.fixture(scope="class")
def string_param_not_matching_pattern():
    param = pms.Parameter.builder().name("Fake String Param") \
        .default("Not empty!").value("id.123A") \
        .param_type("string").pattern(r"^id\.[0-9]*$").build()
    return param

@pytest.fixture(scope="class")
def string_param_matching_pattern():
    param = pms.Parameter.builder().name("Fake String Param") \
        .default("Not empty!").value("id.123") \
        .param_type("string").pattern(r"^id\.[0-9]*$").build()
    return param

@pytest.fixture(scope="class")
def string_param_not_matching_choices():
    param = pms.Parameter.builder().name("Fake String Param") \
        .default("Not empty!").value("snail").choices(["horse", "pig"])\
        .param_type("string").build()
    return param

@pytest.fixture(scope="class")
def string_param_matching_choices():
    param = pms.Parameter.builder().name("Fake String Param") \
        .default("Not empty!").value("horse").choices(["horse", "pig"])\
        .param_type("string").build()
    return param

def test_simple_integer_validation(valid_integer_param):
    validator = valid.Validators.get_validator_for_param(valid_integer_param)
    validator.validate()

@pytest.mark.xfail(raises=AttributeError)
def test_simple_integer_out_of_range(invalid_integer_param):
    validator = valid.Validators.get_validator_for_param(invalid_integer_param)
    validator.validate()

@pytest.mark.xfail(raises=AttributeError)
def test_string_with_empty_pattern_and_choices(invalid_string_param_without_pattern_and_choices):
    validator = valid.Validators.get_validator_for_param(invalid_integer_param)
    validator.validate()

@pytest.mark.xfail(raises=LookupError)
def test_param_with_empty_type(param_with_unknown_type):
    validator = valid.Validators.get_validator_for_param(param_with_unknown_type)
    validator.validate()

@pytest.mark.xfail(raises=AttributeError)
def test_string_param_not_matching_pattern(string_param_not_matching_pattern):
    validator = valid.Validators.get_validator_for_param(string_param_not_matching_pattern)
    validator.validate()

def test_string_param_matching_pattern(string_param_matching_pattern):
    validator = valid.Validators.get_validator_for_param(string_param_matching_pattern)
    validator.validate()

@pytest.mark.xfail(raises=AttributeError)
def test_string_param_not_matching_choices(string_param_not_matching_choices):
    validator = valid.Validators.get_validator_for_param(string_param_not_matching_choices)
    validator.validate()

def test_string_param_matching_choices(string_param_matching_choices):
    validator = valid.Validators.get_validator_for_param(string_param_matching_choices)
    validator.validate()