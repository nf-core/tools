#!/usr/bin/env python
""" Code to deal with pipeline JSON Schema """

from __future__ import print_function

import click
import json
import jsonschema
import logging
import os
import re
import requests
import requests_cache
import subprocess
import sys
import time
import webbrowser
import yaml

import nf_core.utils
import nf_core.launch


class PipelineSchema (object):
    """ Class to generate a schema object with
    functions to handle pipeline JSON Schema """

    def __init__(self):
        """ Initialise the object """

        self.schema = None
        self.schema_filename = None
        self.input_params = {}
        self.pipeline_params = {}
        self.schema_from_scratch = False
        self.no_prompts = False
        self.web_only = False
        self.web_schema_build_url = 'https://nf-co.re/json_schema_build'
        self.web_schema_build_web_url = None
        self.web_schema_build_api_url = None

    def lint_schema(self, schema_filename=None):
        """ Lint a given schema to see if it looks valid """

        if schema_filename is not None:
            if os.path.isdir(schema_filename):
                self.schema_filename = os.path.join(schema_filename, 'nextflow_schema.json')
            else:
                self.schema_filename = schema_filename

        try:
            assert os.path.exists(self.schema_filename)
            assert os.path.isfile(self.schema_filename)
        except AssertionError as e:
            error_msg = "Schema filename not found: {}".format(self.schema_filename)
            logging.error(click.style(error_msg, fg='red'))
            raise AssertionError(error_msg)

        try:
            self.load_schema()
            self.validate_schema()
        except json.decoder.JSONDecodeError as e:
            error_msg = "Could not parse JSON:\n {}".format(e)
            logging.error(click.style(error_msg, fg='red'))
            raise AssertionError(error_msg)
        except AssertionError as e:
            error_msg = "[✗] JSON Schema does not follow nf-core specs:\n {}".format(e)
            logging.error(click.style(error_msg, fg='red'))
            raise AssertionError(error_msg)
        else:
            logging.info(click.style("[✓] Pipeline schema looks valid", fg='green'))

    def get_schema_from_name(self, pipeline):
        """ Given a pipeline name, try to get the JSON Schema """

        # Supplied path exists - assume a local pipeline directory or schema
        if os.path.exists(pipeline):
            if os.path.basename(pipeline) == 'nextflow_schema.json':
                self.schema_filename = pipeline
            else:
                self.schema_filename = os.path.join(pipeline, 'nextflow_schema.json')

        # Path does not exist - assume a name of a remote workflow
        else:
            wf = nf_core.launch.Launch(pipeline)
            wf.get_local_wf()
            self.schema_filename = os.path.join(wf.local_wf.local_path, 'nextflow_schema.json')

        # Check that the schema file exists
        if not os.path.exists(self.schema_filename):
            error = "Could not find pipeline schema for '{}': {}".format(pipeline, self.schema_filename)
            logging.error(error)
            raise AssertionError(error)

        # Load and check schema
        return self.lint_schema()

    def load_schema(self):
        """ Load a JSON Schema from a file """
        with open(self.schema_filename, 'r') as fh:
            self.schema = json.load(fh)
        logging.debug("JSON file loaded: {}".format(self.schema_filename))

    def save_schema(self):
        """ Load a JSON Schema from a file """
        # Write results to a JSON file
        logging.info("Writing JSON schema with {} params: {}".format(len(self.schema['properties']), self.schema_filename))
        with open(self.schema_filename, 'w') as fh:
            json.dump(self.schema, fh, indent=4)

    def load_input_params(self, params_path):
        """ Load a given a path to a parameters file (JSON/YAML)

        These should be input parameters used to run a pipeline with
        the Nextflow -params-file option.
        """
        # First, try to load as JSON
        try:
            with open(params_path, 'r') as fh:
                self.input_params = json.load(fh)
            logging.debug("Loaded JSON input params: {}".format(params_path))
        except Exception as json_e:
            logging.debug("Could not load input params as JSON: {}".format(json_e))
            # This failed, try to load as YAML
            try:
                with open(params_path, 'r') as fh:
                    self.input_params = yaml.safe_load(fh)
                    logging.debug("Loaded YAML input params: {}".format(params_path))
            except Exception as yaml_e:
                error_msg = "Could not load params file as either JSON or YAML:\n JSON: {}\n YAML: {}".format(json_e, yaml_e)
                logging.error(error_msg)
                raise AssertionError(error_msg)

    def validate_params(self):
        """ Check given parameters against a schema and validate """
        try:
            jsonschema.validate(self.input_params, self.schema)
        except jsonschema.exceptions.ValidationError as e:
            logging.error(click.style("[✗] Input parameters are invalid: {}".format(e.message), fg='red'))
            return False
        logging.info(click.style("[✓] Input parameters look valid", fg='green'))
        return True


    def validate_schema(self):
        """ Check that the Schema is valid """
        try:
            jsonschema.Draft7Validator.check_schema(self.schema)
            logging.debug("JSON Schema Draft7 validated")
        except jsonschema.exceptions.SchemaError as e:
            raise AssertionError("Schema does not validate as Draft 7 JSON Schema:\n {}".format(e))

        # Check for nf-core schema keys
        assert 'properties' in self.schema, "Schema should have 'properties' section"

    def build_schema(self, pipeline_dir, no_prompts, web_only, url):
        """ Interactively build a new JSON Schema for a pipeline """

        if no_prompts:
            self.no_prompts = True
        if web_only:
            self.web_only = True
        if url:
            self.web_schema_build_url = url

        # Load a JSON Schema file if we find one
        self.schema_filename = os.path.join(pipeline_dir, 'nextflow_schema.json')
        if(os.path.exists(self.schema_filename)):
            logging.debug("Parsing existing JSON Schema: {}".format(self.schema_filename))
            try:
                self.load_schema()
            except Exception as e:
                logging.error("Existing JSON Schema found, but it is invalid:\n {}".format(click.style(str(e), fg='red')))
                logging.info(
                    "Please fix or delete this file, then try again.\n" \
                    "For more details, run the following command:\n  " + \
                    click.style("nf-core schema lint {}".format(self.schema_filename), fg='blue')
                )
                sys.exit(1)
            logging.info("Loaded existing JSON schema with {} params: {}\n".format(len(self.schema['properties']), self.schema_filename))
        else:
            logging.debug("Existing JSON Schema not found: {}".format(self.schema_filename))

        # Build a skeleton schema if none already existed
        if not self.schema:
            logging.info("No existing schema found - creating a new one from scratch")
            self.schema_from_scratch = True
            config = nf_core.utils.fetch_wf_config(pipeline_dir)
            self.schema = {
                "$schema": "https://json-schema.org/draft-07/schema",
                "$id": "https://raw.githubusercontent.com/{}/master/nextflow_schema.json".format(config['manifest.name']),
                "title": "{} pipeline parameters".format(config['manifest.name']),
                "description": config['manifest.description'],
                "type": "object",
                "properties": {}
            }

        if not self.web_only:
            self.get_wf_params(pipeline_dir)
            self.remove_schema_notfound_configs()
            self.add_schema_found_configs()
            self.save_schema()

        # If running interactively, send to the web for customisation
        if not self.no_prompts:
            if click.confirm(click.style("\nLaunch web builder for customisation and editing?", fg='magenta'), True):
                self.launch_web_builder()

    def get_wf_params(self, pipeline_dir):
        """
        Load the pipeline parameter defaults using `nextflow config`
        Strip out only the params. values and ignore anything that is not a flat variable
        """
        logging.debug("Collecting pipeline parameter defaults\n")
        config = nf_core.utils.fetch_wf_config(pipeline_dir)
        # Pull out just the params. values
        for ckey, cval in config.items():
            if ckey.startswith('params.'):
                # skip anything that's not a flat variable
                if '.' in ckey[7:]:
                    logging.debug("Skipping pipeline param '{}' because it has nested parameter values".format(ckey))
                    continue
                self.pipeline_params[ckey[7:]] = cval

    def remove_schema_notfound_configs(self):
        """
        Strip out anything from the existing JSON Schema that's not in the nextflow params
        """
        params_removed = []
        # Use iterator so that we can delete the key whilst iterating
        for p_key in [k for k in self.schema['properties'].keys()]:
            # Groups - we assume only one-deep
            if self.schema['properties'][p_key]['type'] == 'object':
                for p_child_key in [k for k in self.schema['properties'][p_key].get('properties', {}).keys()]:
                    if self.prompt_remove_schema_notfound_config(p_child_key):
                        del self.schema['properties'][p_key]['properties'][p_child_key]
                        # Remove required flag if set
                        if p_child_key in self.schema['properties'][p_key].get('required', []):
                            self.schema['properties'][p_key]['required'].remove(p_child_key)
                        # Remove required list if now empty
                        if 'required' in self.schema['properties'][p_key] and len(self.schema['properties'][p_key]['required']) == 0:
                            del self.schema['properties'][p_key]['required']
                        logging.debug("Removing '{}' from JSON Schema".format(p_child_key))
                        params_removed.append(click.style(p_child_key, fg='white', bold=True))

            # Top-level params
            else:
                if self.prompt_remove_schema_notfound_config(p_key):
                    del self.schema['properties'][p_key]
                    # Remove required flag if set
                    if p_key in self.schema.get('required', []):
                        self.schema['required'].remove(p_key)
                    # Remove required list if now empty
                    if 'required' in self.schema and len(self.schema['required']) == 0:
                        del self.schema['required']
                    logging.debug("Removing '{}' from JSON Schema".format(p_key))
                    params_removed.append(click.style(p_key, fg='white', bold=True))


        if len(params_removed) > 0:
            logging.info("Removed {} params from existing JSON Schema that were not found with `nextflow config`:\n {}\n".format(len(params_removed), ', '.join(params_removed)))

        return params_removed

    def prompt_remove_schema_notfound_config(self, p_key):
        """
        Check if a given key is found in the nextflow config params and prompt to remove it if note

        Returns True if it should be removed, False if not.
        """
        if p_key not in self.pipeline_params.keys():
            p_key_nice = click.style('params.{}'.format(p_key), fg='white', bold=True)
            remove_it_nice = click.style('Remove it?', fg='yellow')
            if self.no_prompts or self.schema_from_scratch or click.confirm("Unrecognised '{}' found in schema but not in Nextflow config. {}".format(p_key_nice, remove_it_nice), True):
                return True
        return False

    def add_schema_found_configs(self):
        """
        Add anything that's found in the Nextflow params that's missing in the JSON Schema
        """
        params_added = []
        for p_key, p_val in self.pipeline_params.items():
            # Check if key is in top-level params
            if not p_key in self.schema['properties'].keys():
                # Check if key is in group-level params
                if not any( [ p_key in param.get('properties', {}) for k, param in self.schema['properties'].items() ] ):
                    p_key_nice = click.style('params.{}'.format(p_key), fg='white', bold=True)
                    add_it_nice = click.style('Add to JSON Schema?', fg='cyan')
                    if self.no_prompts or self.schema_from_scratch or click.confirm("Found '{}' in Nextflow config. {}".format(p_key_nice, add_it_nice), True):
                        self.schema['properties'][p_key] = self.build_schema_param(p_key, p_val)
                        logging.debug("Adding '{}' to JSON Schema".format(p_key))
                        params_added.append(click.style(p_key, fg='white', bold=True))
        if len(params_added) > 0:
            logging.info("Added {} params to JSON Schema that were found with `nextflow config`:\n {}".format(len(params_added), ', '.join(params_added)))

        return params_added

    def build_schema_param(self, p_key, p_val, p_schema = None):
        """
        Build a JSON Schema dictionary for an param interactively
        """
        if p_schema is None:
            p_type = "string"
            if isinstance(p_val, bool):
                p_type = 'boolean'
            if isinstance(p_val, int):
                p_type = 'integer'

            p_schema = {
                "type": p_type,
                "default": p_val
            }
        return p_schema

    def launch_web_builder(self):
        """
        Send JSON Schema to web builder and wait for response
        """
        content = {
            'post_content': 'json_schema',
            'api': 'true',
            'version': nf_core.__version__,
            'status': 'waiting_for_user',
            'schema': json.dumps(self.schema)
        }
        try:
            response = requests.post(url=self.web_schema_build_url, data=content)
        except (requests.exceptions.Timeout):
            logging.error("Schema builder URL timed out: {}".format(self.web_schema_build_url))
        except (requests.exceptions.ConnectionError):
            logging.error("Could not connect to schema builder URL: {}".format(self.web_schema_build_url))
        else:
            if response.status_code != 200:
                logging.error("Could not access remote JSON Schema builder: {} (HTML {} Error)".format(self.web_schema_build_url, response.status_code))
                logging.debug("Response content:\n{}".format(response.content))
            else:
                try:
                    web_response = json.loads(response.content)
                    assert 'status' in web_response
                    assert 'api_url' in web_response
                    assert 'web_url' in web_response
                    assert web_response['status'] == 'recieved'
                except (json.decoder.JSONDecodeError, AssertionError) as e:
                    logging.error("JSON Schema builder response not recognised: {}\n See verbose log for full response (nf-core -v schema)".format(self.web_schema_build_url))
                    logging.debug("Response content:\n{}".format(response.content))
                else:
                    self.web_schema_build_web_url = web_response['web_url']
                    self.web_schema_build_api_url = web_response['api_url']
                    logging.info("Opening URL: {}".format(web_response['web_url']))
                    webbrowser.open(web_response['web_url'])
                    logging.info("Waiting for form to be completed in the browser. Use ctrl+c to stop waiting and force exit.")
                    self.get_web_builder_response()

    def get_web_builder_response(self):
        """
        Given a URL for a Schema build response, recursively query it until results are ready.
        Once ready, validate Schema and write to disk.
        """
        # Clear requests_cache so that we get the updated statuses
        requests_cache.clear()
        try:
            response = requests.get(self.web_schema_build_api_url, headers={'Cache-Control': 'no-cache'})
        except (requests.exceptions.Timeout):
            logging.error("Schema builder URL timed out: {}".format(self.web_schema_build_api_url))
        except (requests.exceptions.ConnectionError):
            logging.error("Could not connect to schema builder URL: {}".format(self.web_schema_build_api_url))
        else:
            if response.status_code != 200:
                logging.error("Could not access remote JSON Schema builder results: {} (HTML {} Error)".format(self.web_schema_build_api_url, response.status_code))
                logging.debug("Response content:\n{}".format(response.content))
            else:
                try:
                    web_response = json.loads(response.content)
                    assert 'status' in web_response
                except (json.decoder.JSONDecodeError, AssertionError) as e:
                    logging.error("JSON Schema builder results response not recognised: {}\n See verbose log for full response".format(self.web_schema_build_api_url))
                    logging.debug("Response content:\n{}".format(response.content))
                else:
                    if web_response['status'] == 'error':
                        logging.error("Got error from JSON Schema builder ( {} )".format(click.style(web_response.get('message'), fg='red')))
                    elif web_response['status'] == 'waiting_for_user':
                        time.sleep(5) # wait 5 seconds before trying again
                        sys.stdout.write('.')
                        sys.stdout.flush()
                        self.get_web_builder_response()
                    elif web_response['status'] == 'web_builder_edited':
                        logging.info("Found saved status from nf-core JSON Schema builder")
                        try:
                            self.schema = json.loads(web_response['schema'])
                            self.validate_schema()
                        except json.decoder.JSONDecodeError as e:
                            logging.error("Could not parse returned JSON:\n {}".format(e))
                            sys.exit(1)
                        except AssertionError as e:
                            logging.info("Response from JSON Builder did not pass validation:\n {}".format(e))
                            sys.exit(1)
                        else:
                            self.save_schema()
                    else:
                        logging.error("JSON Schema builder returned unexpected status ({}): {}\n See verbose log for full response".format(web_response['status'], self.web_schema_build_api_url))
                        logging.debug("Response content:\n{}".format(response.content))
