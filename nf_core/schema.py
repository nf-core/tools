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


class PipelineSchema (object):
    """ Class to generate a schema object with
    functions to handle pipeline JSON Schema """

    def __init__(self):
        """ Initialise the object """

        self.schema = None

    def lint_schema(self, schema_path):
        """ Lint a given schema to see if it looks valid """
        try:
            self.load_schema(schema_path)
        except AssertionError:
            sys.exit(1)
        else:
            logging.info("JSON Schema looks valid!")

    def load_schema(self, schema_path):
        """ Load a JSON Schema from a file """
        try:
            with open(schema_path, 'r') as fh:
                self.schema = json.load(fh)
        except json.decoder.JSONDecodeError as e:
            logging.error("Could not parse JSON:\n {}".format(e))
            raise AssertionError
        logging.debug("JSON file loaded: {}".format(schema_path))

        # Check that the Schema is valid
        try:
            jsonschema.Draft7Validator.check_schema(self.schema)
        except jsonschema.exceptions.SchemaError as e:
            logging.error("Schema does not validate as Draft 7 JSONSchema:\n {}".format(e))
            raise AssertionError
