#!/usr/bin/env python
""" Code to deal with pipeline JSON Schema """

from __future__ import print_function
from rich.prompt import Confirm

import copy
import jinja2
import json
import jsonschema
import logging
import os
import requests
import requests_cache
import sys
import time
import webbrowser
import yaml

import nf_core.list, nf_core.utils

log = logging.getLogger(__name__)


class PipelineSchema(object):
    """ Class to generate a schema object with
    functions to handle pipeline JSON Schema """

    def __init__(self):
        """ Initialise the object """

        self.schema = None
        self.pipeline_dir = None
        self.schema_filename = None
        self.schema_defaults = {}
        self.input_params = {}
        self.pipeline_params = {}
        self.pipeline_manifest = {}
        self.schema_from_scratch = False
        self.no_prompts = False
        self.web_only = False
        self.web_schema_build_url = "https://nf-co.re/json_schema_build"
        self.web_schema_build_web_url = None
        self.web_schema_build_api_url = None

    def get_schema_path(self, path, local_only=False, revision=None):
        """ Given a pipeline name, directory, or path, set self.schema_filename """

        # Supplied path exists - assume a local pipeline directory or schema
        if os.path.exists(path):
            if revision is not None:
                log.warning("Local workflow supplied, ignoring revision '{}'".format(revision))
            if os.path.isdir(path):
                self.pipeline_dir = path
                self.schema_filename = os.path.join(path, "nextflow_schema.json")
            else:
                self.pipeline_dir = os.path.dirname(path)
                self.schema_filename = path

        # Path does not exist - assume a name of a remote workflow
        elif not local_only:
            self.pipeline_dir = nf_core.list.get_local_wf(path, revision=revision)
            self.schema_filename = os.path.join(self.pipeline_dir, "nextflow_schema.json")

        # Only looking for local paths, overwrite with None to be safe
        else:
            self.schema_filename = None

        # Check that the schema file exists
        if self.schema_filename is None or not os.path.exists(self.schema_filename):
            error = "Could not find pipeline schema for '{}': {}".format(path, self.schema_filename)
            log.error(error)
            raise AssertionError(error)

    def load_lint_schema(self):
        """ Load and lint a given schema to see if it looks valid """
        try:
            self.load_schema()
            self.validate_schema(self.schema)
        except json.decoder.JSONDecodeError as e:
            error_msg = "Could not parse JSON:\n {}".format(e)
            log.error(error_msg)
            raise AssertionError(error_msg)
        except AssertionError as e:
            error_msg = "[red][[✗]] JSON Schema does not follow nf-core specs:\n {}".format(e)
            log.error(error_msg)
            raise AssertionError(error_msg)
        else:
            try:
                self.get_schema_defaults()
                self.validate_schema(self.schema)
            except AssertionError as e:
                error_msg = "[red][[✗]] Flattened JSON Schema does not follow nf-core specs:\n {}".format(e)
                log.error(error_msg)
                raise AssertionError(error_msg)
            else:
                log.info("[green][[✓]] Pipeline schema looks valid")

    def load_schema(self):
        """ Load a JSON Schema from a file """
        with open(self.schema_filename, "r") as fh:
            self.schema = json.load(fh)
        log.debug("JSON file loaded: {}".format(self.schema_filename))

    def get_schema_defaults(self):
        """ Generate set of input parameters from flattened schema """
        # Top level schema-properties (ungrouped)
        for p_key, param in self.schema.get("properties", {}).items():
            if "default" in param:
                self.schema_defaults[p_key] = param["default"]

        # TODO: Grouped schema properties in subschema definitions
        for d_key, definition in self.schema.get("definitions", {}).items():
            for p_key, param in definition.get("properties", {}).items():
                if "default" in param:
                    self.schema_defaults[p_key] = param["default"]

    def save_schema(self):
        """ Load a JSON Schema from a file """
        # Write results to a JSON file
        log.info("Writing JSON schema with {} params: {}".format(len(self.schema["properties"]), self.schema_filename))
        with open(self.schema_filename, "w") as fh:
            json.dump(self.schema, fh, indent=4)

    def load_input_params(self, params_path):
        """ Load a given a path to a parameters file (JSON/YAML)

        These should be input parameters used to run a pipeline with
        the Nextflow -params-file option.
        """
        # First, try to load as JSON
        try:
            with open(params_path, "r") as fh:
                params = json.load(fh)
                self.input_params.update(params)
            log.debug("Loaded JSON input params: {}".format(params_path))
        except Exception as json_e:
            log.debug("Could not load input params as JSON: {}".format(json_e))
            # This failed, try to load as YAML
            try:
                with open(params_path, "r") as fh:
                    params = yaml.safe_load(fh)
                    self.input_params.update(params)
                    log.debug("Loaded YAML input params: {}".format(params_path))
            except Exception as yaml_e:
                error_msg = "Could not load params file as either JSON or YAML:\n JSON: {}\n YAML: {}".format(
                    json_e, yaml_e
                )
                log.error(error_msg)
                raise AssertionError(error_msg)

    def validate_params(self):
        """ Check given parameters against a schema and validate """
        try:
            assert self.schema is not None
            jsonschema.validate(self.input_params, self.schema)
        except AssertionError:
            log.error("[red][[✗]] Flattened JSON Schema not found")
            return False
        except jsonschema.exceptions.ValidationError as e:
            log.error("[red][[✗]] Input parameters are invalid: {}".format(e.message))
            return False
        log.info("[green][[✓]] Input parameters look valid")
        return True

    def validate_schema(self, schema):
        """ Check that the Schema is valid """
        try:
            jsonschema.Draft7Validator.check_schema(schema)
            log.debug("JSON Schema Draft7 validated")
        except jsonschema.exceptions.SchemaError as e:
            raise AssertionError("Schema does not validate as Draft 7 JSON Schema:\n {}".format(e))

    def make_skeleton_schema(self):
        """ Make a new JSON Schema from the template """
        self.schema_from_scratch = True
        # Use Jinja to render the template schema file to a variable
        # Bit confusing sorry, but cookiecutter only works with directories etc so this saves a bunch of code
        templateLoader = jinja2.FileSystemLoader(
            searchpath=os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "pipeline-template", "{{cookiecutter.name_noslash}}"
            )
        )
        templateEnv = jinja2.Environment(loader=templateLoader)
        schema_template = templateEnv.get_template("nextflow_schema.json")
        cookiecutter_vars = {
            "name": self.pipeline_manifest.get("name", os.path.dirname(self.schema_filename)).strip("'"),
            "description": self.pipeline_manifest.get("description", "").strip("'"),
        }
        self.schema = json.loads(schema_template.render(cookiecutter=cookiecutter_vars))

    def build_schema(self, pipeline_dir, no_prompts, web_only, url):
        """ Interactively build a new JSON Schema for a pipeline """

        if no_prompts:
            self.no_prompts = True
        if web_only:
            self.web_only = True
        if url:
            self.web_schema_build_url = url

        # Get JSON Schema filename
        try:
            self.get_schema_path(pipeline_dir, local_only=True)
        except AssertionError:
            log.info("No existing schema found - creating a new one from the nf-core template")
            self.get_wf_params()
            self.make_skeleton_schema()
            self.remove_schema_notfound_configs()
            self.add_schema_found_configs()
            self.save_schema()

        # Load and validate Schema
        try:
            self.load_lint_schema()
        except AssertionError as e:
            log.error("Existing JSON Schema found, but it is invalid: {}".format(self.schema_filename))
            log.info("Please fix or delete this file, then try again.")
            return False

        if not self.web_only:
            self.get_wf_params()
            self.remove_schema_notfound_configs()
            self.add_schema_found_configs()
            self.save_schema()

        # If running interactively, send to the web for customisation
        if not self.no_prompts:
            if Confirm.ask(":rocket: Launch web builder for customisation and editing?"):
                try:
                    self.launch_web_builder()
                except AssertionError as e:
                    log.error(e.args[0])
                    # Extra help for people running offline
                    if "Could not connect" in e.args[0]:
                        log.info(
                            "If you're working offline, now copy your schema ({}) and paste at https://nf-co.re/json_schema_build".format(
                                self.schema_filename
                            )
                        )
                        log.info("When you're finished, you can paste the edited schema back into the same file")
                    if self.web_schema_build_web_url:
                        log.info(
                            "To save your work, open {}\n"
                            "Click the blue 'Finished' button, copy the schema and paste into this file: {}".format(
                                self.web_schema_build_web_url, self.schema_filename
                            )
                        )
                    return False

    def get_wf_params(self):
        """
        Load the pipeline parameter defaults using `nextflow config`
        Strip out only the params. values and ignore anything that is not a flat variable
        """
        # Check that we haven't already pulled these (eg. skeleton schema)
        if len(self.pipeline_params) > 0 and len(self.pipeline_manifest) > 0:
            log.debug("Skipping get_wf_params as we already have them")
            return

        log.debug("Collecting pipeline parameter defaults\n")
        config = nf_core.utils.fetch_wf_config(os.path.dirname(self.schema_filename))
        skipped_params = []
        # Pull out just the params. values
        for ckey, cval in config.items():
            if ckey.startswith("params."):
                # skip anything that's not a flat variable
                if "." in ckey[7:]:
                    skipped_params.append(ckey)
                    continue
                self.pipeline_params[ckey[7:]] = cval
            if ckey.startswith("manifest."):
                self.pipeline_manifest[ckey[9:]] = cval
        # Log skipped params
        if len(skipped_params) > 0:
            log.debug(
                "Skipped following pipeline params because they had nested parameter values:\n{}".format(
                    ", ".join(skipped_params)
                )
            )

    def remove_schema_notfound_configs(self):
        """
        Strip out anything from the existing JSON Schema that's not in the nextflow params
        """
        params_removed = []
        # Use iterator so that we can delete the key whilst iterating
        for p_key in [k for k in self.schema["properties"].keys()]:
            # Groups - we assume only one-deep
            if self.schema["properties"][p_key]["type"] == "object":
                for p_child_key in [k for k in self.schema["properties"][p_key].get("properties", {}).keys()]:
                    if self.prompt_remove_schema_notfound_config(p_child_key):
                        del self.schema["properties"][p_key]["properties"][p_child_key]
                        # Remove required flag if set
                        if p_child_key in self.schema["properties"][p_key].get("required", []):
                            self.schema["properties"][p_key]["required"].remove(p_child_key)
                        # Remove required list if now empty
                        if (
                            "required" in self.schema["properties"][p_key]
                            and len(self.schema["properties"][p_key]["required"]) == 0
                        ):
                            del self.schema["properties"][p_key]["required"]
                        log.debug("Removing '{}' from JSON Schema".format(p_child_key))
                        params_removed.append(p_child_key)

            # Top-level params
            else:
                if self.prompt_remove_schema_notfound_config(p_key):
                    del self.schema["properties"][p_key]
                    # Remove required flag if set
                    if p_key in self.schema.get("required", []):
                        self.schema["required"].remove(p_key)
                    # Remove required list if now empty
                    if "required" in self.schema and len(self.schema["required"]) == 0:
                        del self.schema["required"]
                    log.debug("Removing '{}' from JSON Schema".format(p_key))
                    params_removed.append(p_key)

        return params_removed

    def prompt_remove_schema_notfound_config(self, p_key):
        """
        Check if a given key is found in the nextflow config params and prompt to remove it if note

        Returns True if it should be removed, False if not.
        """
        if p_key not in self.pipeline_params.keys():
            if self.no_prompts or self.schema_from_scratch:
                return True
            if Confirm.ask(
                ":question: Unrecognised [white bold]'params.{}'[/] found in schema but not pipeline! [yellow]Remove it?".format(
                    p_key
                )
            ):
                return True
        return False

    def add_schema_found_configs(self):
        """
        Add anything that's found in the Nextflow params that's missing in the JSON Schema
        """
        params_added = []
        for p_key, p_val in self.pipeline_params.items():
            # Check if key is in top-level params
            if not p_key in self.schema["properties"].keys():
                # Check if key is in group-level params
                if not any([p_key in param.get("properties", {}) for k, param in self.schema["properties"].items()]):
                    if (
                        self.no_prompts
                        or self.schema_from_scratch
                        or Confirm.ask(
                            ":sparkles: Found [white bold]'params.{}'[/] in pipeline but not in schema! [blue]Add to JSON Schema?".format(
                                p_key
                            )
                        )
                    ):
                        self.schema["properties"][p_key] = self.build_schema_param(p_val)
                        log.debug("Adding '{}' to JSON Schema".format(p_key))
                        params_added.append(p_key)

        return params_added

    def build_schema_param(self, p_val):
        """
        Build a JSON Schema dictionary for an param interactively
        """
        p_val = p_val.strip("\"'")
        # p_val is always a string as it is parsed from nextflow config this way
        try:
            p_val = float(p_val)
            if p_val == int(p_val):
                p_val = int(p_val)
                p_type = "integer"
            else:
                p_type = "number"
        except ValueError:
            p_type = "string"

        # NB: Only test "True" for booleans, as it is very common to initialise
        # an empty param as false when really we expect a string at a later date..
        if p_val == "True":
            p_val = True
            p_type = "boolean"

        p_schema = {"type": p_type, "default": p_val}

        # Assume that false and empty strings shouldn't be a default
        if p_val == "false" or p_val == "":
            del p_schema["default"]

        return p_schema

    def launch_web_builder(self):
        """
        Send JSON Schema to web builder and wait for response
        """
        content = {
            "post_content": "json_schema",
            "api": "true",
            "version": nf_core.__version__,
            "status": "waiting_for_user",
            "schema": json.dumps(self.schema),
        }
        web_response = nf_core.utils.poll_nfcore_web_api(self.web_schema_build_url, content)
        try:
            assert "api_url" in web_response
            assert "web_url" in web_response
            assert web_response["status"] == "recieved"
        except (AssertionError) as e:
            log.debug("Response content:\n{}".format(json.dumps(web_response, indent=4)))
            raise AssertionError(
                "JSON Schema builder response not recognised: {}\n See verbose log for full response (nf-core -v schema)".format(
                    self.web_schema_build_url
                )
            )
        else:
            self.web_schema_build_web_url = web_response["web_url"]
            self.web_schema_build_api_url = web_response["api_url"]
            log.info("Opening URL: {}".format(web_response["web_url"]))
            webbrowser.open(web_response["web_url"])
            log.info("Waiting for form to be completed in the browser. Remember to click Finished when you're done.\n")
            nf_core.utils.wait_cli_function(self.get_web_builder_response)

    def get_web_builder_response(self):
        """
        Given a URL for a Schema build response, recursively query it until results are ready.
        Once ready, validate Schema and write to disk.
        """
        web_response = nf_core.utils.poll_nfcore_web_api(self.web_schema_build_api_url)
        if web_response["status"] == "error":
            raise AssertionError("Got error from JSON Schema builder ( {} )".format(web_response.get("message")))
        elif web_response["status"] == "waiting_for_user":
            return False
        elif web_response["status"] == "web_builder_edited":
            log.info("Found saved status from nf-core JSON Schema builder")
            try:
                self.schema = web_response["schema"]
                self.validate_schema(self.schema)
            except AssertionError as e:
                raise AssertionError("Response from JSON Builder did not pass validation:\n {}".format(e))
            else:
                self.save_schema()
                return True
        else:
            log.debug("Response content:\n{}".format(json.dumps(web_response, indent=4)))
            raise AssertionError(
                "JSON Schema builder returned unexpected status ({}): {}\n See verbose log for full response".format(
                    web_response["status"], self.web_schema_build_api_url
                )
            )
