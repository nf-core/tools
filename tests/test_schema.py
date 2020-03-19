#!/usr/bin/env python
""" Tests covering the pipeline schema code.
"""

import nf_core.schema

import click
import json
import mock
import os
import git
import pytest
import requests
import tempfile
import time
import unittest
import yaml

class TestSchema(unittest.TestCase):
    """Class for schema tests"""

    def setUp(self):
        """ Create a new PipelineSchema object """
        self.schema_obj = nf_core.schema.PipelineSchema()
        self.root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(self.root_repo_dir, 'nf_core', 'pipeline-template', '{{cookiecutter.name_noslash}}')
        self.template_schema = os.path.join(self.template_dir, 'nextflow_schema.json')

    def test_lint_schema(self):
        """ Check linting with the pipeline template directory """
        self.schema_obj.lint_schema(self.template_dir)

    @pytest.mark.xfail(raises=AssertionError)
    def test_lint_schema_nofile(self):
        """ Check that linting raises properly if a non-existant file is given """
        self.schema_obj.lint_schema('fake_file')

    def test_get_schema_from_name_path(self):
        """ Get schema file from directory """
        self.schema_obj.get_schema_from_name(self.template_dir)

    # TODO - Update when we do have a released pipeline with a valid schema
    @pytest.mark.xfail(raises=AssertionError)
    def test_get_schema_from_name_name(self):
        """ Get schema file from the name of a remote pipeline """
        self.schema_obj.get_schema_from_name('atacseq')

    @pytest.mark.xfail(raises=AssertionError)
    def test_get_schema_from_name_name_notexist(self):
        """
        Get schema file from the name of a remote pipeline
        that doesn't have a schema file
        """
        self.schema_obj.get_schema_from_name('exoseq')

    def test_load_schema(self):
        """ Try to load a schema from a file """
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()

    def test_save_schema(self):
        """ Try to save a schema """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()

        # Make a temporary file to write schema to
        tmp_file = tempfile.NamedTemporaryFile()
        self.schema_obj.schema_filename = tmp_file.name
        self.schema_obj.save_schema()

    def test_load_input_params_json(self):
        """ Try to load a JSON file with params for a pipeline run """
        # Make a temporary file to write schema to
        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, 'w') as fh:
            json.dump({'reads': 'fubar'}, fh)
        self.schema_obj.load_input_params(tmp_file.name)

    def test_load_input_params_yaml(self):
        """ Try to load a YAML file with params for a pipeline run """
        # Make a temporary file to write schema to
        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, 'w') as fh:
            yaml.dump({'reads': 'fubar'}, fh)
        self.schema_obj.load_input_params(tmp_file.name)

    @pytest.mark.xfail(raises=AssertionError)
    def test_load_input_params_invalid(self):
        """ Check failure when a non-existent file params file is loaded """
        self.schema_obj.load_input_params('fubar')

    def test_validate_params_pass(self):
        """ Try validating a set of parameters against a schema """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()
        self.schema_obj.input_params = {'reads': 'fubar'}
        assert self.schema_obj.validate_params()

    def test_validate_params_fail(self):
        """ Check that False is returned if params don't validate against a schema """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()
        self.schema_obj.input_params = {'fubar': 'reads'}
        assert not self.schema_obj.validate_params()

    def test_validate_schema_pass(self):
        """ Check that the schema validation passes """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()
        self.schema_obj.validate_schema()

    @pytest.mark.xfail(raises=AssertionError)
    def test_validate_schema_fail_notjsonschema(self):
        """ Check that the schema validation fails when not JSONSchema """
        self.schema_obj.schema = {'type': 'invalidthing'}
        self.schema_obj.validate_schema()

    @pytest.mark.xfail(raises=AssertionError)
    def test_validate_schema_fail_nfcore(self):
        """ Check that the schema validation fails nf-core addons """
        self.schema_obj.schema = {}
        self.schema_obj.validate_schema()

    def test_make_skeleton_schema(self):
        """ Test making a new schema skeleton """
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.make_skeleton_schema()
        self.schema_obj.validate_schema()

    def test_get_wf_params(self):
        """ Test getting the workflow parameters from a pipeline """
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.get_wf_params()

    def test_prompt_remove_schema_notfound_config_returntrue(self):
        """ Remove unrecognised params from the schema """
        self.schema_obj.pipeline_params = {'foo': 'bar'}
        self.schema_obj.no_prompts = True
        assert self.schema_obj.prompt_remove_schema_notfound_config('baz')

    def test_prompt_remove_schema_notfound_config_returnfalse(self):
        """ Do not temove unrecognised params from the schema """
        self.schema_obj.pipeline_params = {'foo': 'bar'}
        self.schema_obj.no_prompts = True
        assert not self.schema_obj.prompt_remove_schema_notfound_config('foo')

    def test_remove_schema_notfound_configs(self):
        """ Remove unrecognised params from the schema """
        self.schema_obj.schema = {
            'properties': {
                'foo': {
                    'type': 'string'
                }
            },
            'required': ['foo']
        }
        self.schema_obj.pipeline_params = {'bar': True}
        self.schema_obj.no_prompts = True
        params_removed = self.schema_obj.remove_schema_notfound_configs()
        assert len(self.schema_obj.schema['properties']) == 0
        assert len(params_removed) == 1
        assert click.style('foo', fg='white', bold=True) in params_removed

    def test_remove_schema_notfound_configs_childobj(self):
        """
        Remove unrecognised params from the schema,
        even when they're in a group
        """
        self.schema_obj.schema = {
            'properties': {
                'parent': {
                    'type': 'object',
                    'properties': {
                        'foo': {
                            'type': 'string'
                        }
                    },
                    'required': ['foo']
                }
            }
        }
        self.schema_obj.pipeline_params = {'bar': True}
        self.schema_obj.no_prompts = True
        params_removed = self.schema_obj.remove_schema_notfound_configs()
        assert len(self.schema_obj.schema['properties']['parent']['properties']) == 0
        assert len(params_removed) == 1
        assert click.style('foo', fg='white', bold=True) in params_removed

    def test_add_schema_found_configs(self):
        """ Try adding a new parameter to the schema from the config """
        self.schema_obj.pipeline_params = {
            'foo': 'bar'
        }
        self.schema_obj.schema = { 'properties': {} }
        self.schema_obj.no_prompts = True
        params_added = self.schema_obj.add_schema_found_configs()
        assert len(self.schema_obj.schema['properties']) == 1
        assert len(params_added) == 1
        assert click.style('foo', fg='white', bold=True) in params_added

    def test_build_schema_param_str(self):
        """ Build a new schema param from a config value (string) """
        param = self.schema_obj.build_schema_param('foo')
        assert param == {
            'type': 'string',
            'default': 'foo'
        }

    def test_build_schema_param_bool(self):
        """ Build a new schema param from a config value (bool) """
        param = self.schema_obj.build_schema_param(True)
        print(param)
        assert param == {
            'type': 'boolean',
            'default': True
        }

    def test_build_schema_param_int(self):
        """ Build a new schema param from a config value (int) """
        param = self.schema_obj.build_schema_param(12)
        assert param == {
            'type': 'integer',
            'default': 12
        }

    def test_build_schema_param_int(self):
        """ Build a new schema param from a config value (float) """
        param = self.schema_obj.build_schema_param(12.34)
        assert param == {
            'type': 'number',
            'default': 12.34
        }

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch('requests.post')
    def test_launch_web_builder_timeout(self, mock_post):
        """ Mock launching the web builder, but timeout on the request """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.Timeout()
        self.schema_obj.launch_web_builder()

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch('requests.post')
    def test_launch_web_builder_connection_error(self, mock_post):
        """ Mock launching the web builder, but get a connection error """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.ConnectionError()
        self.schema_obj.launch_web_builder()

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch('requests.post')
    def test_get_web_builder_response_timeout(self, mock_post):
        """ Mock chekcing for a web builder response, but timeout on the request """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.Timeout()
        self.schema_obj.launch_web_builder()

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch('requests.post')
    def test_get_web_builder_response_connection_error(self, mock_post):
        """ Mock chekcing for a web builder response, but get a connection error """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.ConnectionError()
        self.schema_obj.launch_web_builder()

    def mocked_requests_post(**kwargs):
        """ Helper function to emulate requests responses from the web """

        class MockResponse:
            def __init__(self, data, status_code):
                self.status_code = status_code
                self.content = json.dumps(data)

        if kwargs['url'] == 'invalid_url':
            return MockResponse({}, 404)

        if kwargs['url'] == 'valid_url':
            response_data = {
                'status': 'recieved',
                'api_url': 'foo',
                'web_url': 'bar'
            }
            return MockResponse(response_data, 200)

    def mocked_requests_get(*args, **kwargs):
        """ Helper function to emulate requests responses from the web """

        class MockResponse:
            def __init__(self, data, status_code):
                self.status_code = status_code
                self.content = json.dumps(data)

        if args[0] == 'invalid_url':
            return MockResponse({}, 404)

        if args[0] == 'valid_url':
            response_data = {
                'status': 'recieved',
                'api_url': 'foo',
                'web_url': 'bar'
            }
            return MockResponse(response_data, 200)

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch('requests.post', side_effect=mocked_requests_post)
    def test_launch_web_builder_404(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_url = 'invalid_url'
        self.schema_obj.launch_web_builder()


    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch('requests.get', side_effect=mocked_requests_get)
    def test_get_web_builder_response_404(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_api_url = 'invalid_url'
        self.schema_obj.get_web_builder_response()
