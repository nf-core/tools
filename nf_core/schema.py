#!/usr/bin/env python
""" Code to deal with pipeline JSON Schema """

from __future__ import print_function

import click
import json
import jsonschema
import logging
import os
import re
import subprocess
import sys

import nf_core.utils


class PipelineSchema (object):
    """ Class to generate a schema object with
    functions to handle pipeline JSON Schema """

    def __init__(self):
        """ Initialise the object """

        self.schema = None
        self.pipeline_params = {}
        self.use_defaults = False

    def lint_schema(self, schema_path):
        """ Lint a given schema to see if it looks valid """
        try:
            self.load_schema(schema_path)
        except json.decoder.JSONDecodeError as e:
            logging.error("Could not parse JSON:\n {}".format(e))
            sys.exit(1)
        except AssertionError as e:
            logging.info("JSON Schema does not follow nf-core specs:\n {}".format(e))
            sys.exit(1)
        except jsonschema.exceptions.SchemaError as e:
            logging.error("Schema does not validate as Draft 7 JSONSchema:\n {}".format(e))
            sys.exit(1)
        else:
            logging.info("JSON Schema looks valid!")

    def load_schema(self, schema_path):
        """ Load a JSON Schema from a file """
        with open(schema_path, 'r') as fh:
            self.schema = json.load(fh)
        logging.debug("JSON file loaded: {}".format(schema_path))

        # Check that the Schema is valid
        jsonschema.Draft7Validator.check_schema(self.schema)
        logging.debug("JSON Schema Draft7 validated")

        # Check for nf-core schema keys
        assert 'properties' in self.schema, "Schema should have 'properties' section"
        assert 'input' in self.schema['properties'], "properties should have section 'input'"
        assert 'properties' in self.schema['properties']['input'], "properties.input should have section 'properties'"

    def build_schema(self, pipeline_dir, use_defaults):
        """ Interactively build a new JSON Schema for a pipeline """

        if use_defaults:
            self.use_defaults = True

        # Load a JSON Schema file if we find one
        pipeline_schema_file = os.path.join(pipeline_dir, 'parameters.settings.json')
        if(os.path.exists(pipeline_schema_file)):
            logging.debug("Parsing existing JSON Schema: {}".format(pipeline_schema_file))
            try:
                self.load_schema(pipeline_schema_file)
            except Exception as e:
                logging.error("Existing JSON Schema found, but it is invalid:\n {}".format(click.style(str(e), fg='red')))
                logging.info(
                    "Please fix or delete this file, then try again.\n" \
                    "For more details, run the following command:\n  " + \
                    click.style("nf-core schema lint {}".format(pipeline_schema_file), fg='blue')
                )
                sys.exit(1)
            logging.info("Loaded existing JSON schema with {} params: {}\n".format(len(self.schema['properties']['input']['properties']), pipeline_schema_file))
        else:
            logging.debug("Existing JSON Schema not found: {}".format(pipeline_schema_file))

        self.get_wf_params(pipeline_dir)
        self.remove_schema_notfound_config()
        self.add_schema_found_config()

        # Write results to a JSON file
        logging.info("Writing JSON schema with {} params: {}".format(len(self.schema['properties']['input']['properties']), pipeline_schema_file))
        with open(pipeline_schema_file, 'w') as fh:
            json.dump(self.schema, fh, indent=4)

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

    def remove_schema_notfound_config(self):
        """
        Strip out anything from the existing JSON Schema that's not in the nextflow params
        """
        params_removed = []
        # Use iterator so that we can delete the key whilst iterating
        for p_key in [k for k in self.schema['properties']['input']['properties'].keys()]:
            if p_key not in self.pipeline_params.keys():
                p_key_nice = click.style('params.{}'.format(p_key), fg='white', bold=True)
                remove_it_nice = click.style('Remove it?', fg='yellow')
                if self.use_defaults or click.confirm("Unrecognised '{}' found in schema but not in Nextflow config. {}".format(p_key_nice, remove_it_nice), True):
                    del self.schema['properties']['input']['properties'][p_key]
                    logging.debug("Removing '{}' from JSON Schema".format(p_key))
                    params_removed.append(click.style(p_key, fg='white', bold=True))
        if len(params_removed) > 0:
            logging.info("Removed {} inputs from existing JSON Schema that were not found with `nextflow config`:\n {}\n".format(len(params_removed), ', '.join(params_removed)))

    def add_schema_found_config(self):
        """
        Add anything that's found in the Nextflow params that's missing in the JSON Schema
        """
        params_added = []
        for p_key, p_val in self.pipeline_params.items():
            if p_key not in self.schema['properties']['input']['properties'].keys():
                p_key_nice = click.style('params.{}'.format(p_key), fg='white', bold=True)
                add_it_nice = click.style('Add to JSON Schema?', fg='cyan')
                if self.use_defaults or click.confirm("Found '{}' in Nextflow config. {}".format(p_key_nice, add_it_nice), True):
                    self.schema['properties']['input'][p_key] = self.build_schema_input(p_key, p_val)
                    logging.debug("Adding '{}' to JSON Schema".format(p_key))
                    params_added.append(click.style(p_key, fg='white', bold=True))
        if len(params_added) > 0:
            logging.info("Added {} inputs to JSON Schema that were found with `nextflow config`:\n {}".format(len(params_added), ', '.join(params_added)))

    def build_schema_input(self, p_key, p_val, p_schema = None):
        """
        Build a JSON Schema dictionary for an input interactively
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
