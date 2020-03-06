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
        self.quiet = False

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

    def build_schema(self, pipeline_dir, quiet):
        """ Interactively build a new JSON Schema for a pipeline """

        if quiet:
            self.quiet = True

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
            logging.info("Loaded existing JSON schema with {} params: {}".format(len(self.schema['properties']['input']), pipeline_schema_file))
        else:
            logging.debug("Existing JSON Schema not found: {}".format(pipeline_schema_file))

        self.get_wf_params(pipeline_dir)
        self.remove_schema_notfound_config()
        self.add_schema_found_config()

        # Write results to a JSON file
        logging.info("Writing JSON schema with {} params: {}".format(len(self.schema['properties']['input']), pipeline_schema_file))
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
        # Use iterator so that we can delete the key whilst iterating
        for p_key in [k for k in self.schema['properties']['input'].keys()]:
            if p_key not in self.pipeline_params.keys():
                if self.quiet or click.confirm("Parameter '{}' found in schema but not in Nextflow config. Remove it?".format(p_key), True):
                    del self.schema['properties']['input'][p_key]
                    logging.debug("Removing '{}' from JSON Schema".format(p_key))

    def add_schema_found_config(self):
        """
        Add anything that's found in the Nextflow params that's missing in the JSON Schema
        """
        for p_key, p_val in self.pipeline_params.items():
            if p_key not in self.schema['properties']['input'].keys():
                if self.quiet or click.confirm("Parameter '{}' found in Nextflow config but not in JSON Schema. Add it?".format(p_key), True):
                    self.schema['properties']['input'][p_key] = self.prompt_config_input(p_key, p_val)
                    logging.debug("Adding '{}' to JSON Schema".format(p_key))

    def prompt_config_input(self, p_key, p_val, p_schema = None):
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
        if self.quiet:
            return p_schema
        else:
            logging.warn("prompt_config_input not finished")
            return p_schema
