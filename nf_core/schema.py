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
import copy

import nf_core.list, nf_core.utils

log = logging.getLogger(__name__)


class PipelineSchema(object):
    """Class to generate a schema object with
    functions to handle pipeline JSON Schema"""

    def __init__(self):
        """Initialise the object"""

        self.schema = None
        self.pipeline_dir = None
        self.schema_filename = None
        self.schema_defaults = {}
        self.schema_params = []
        self.input_params = {}
        self.pipeline_params = {}
        self.pipeline_manifest = {}
        self.schema_from_scratch = False
        self.no_prompts = False
        self.web_only = False
        self.web_schema_build_url = "https://nf-co.re/pipeline_schema_builder"
        self.web_schema_build_web_url = None
        self.web_schema_build_api_url = None

    def get_schema_path(self, path, local_only=False, revision=None):
        """Given a pipeline name, directory, or path, set self.schema_filename"""

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
        """Load and lint a given schema to see if it looks valid"""
        try:
            self.load_schema()
            num_params = self.validate_schema()
            self.get_schema_defaults()
            self.validate_default_params()
            log.info("[green][✓] Pipeline schema looks valid[/] [dim](found {} params)".format(num_params))
        except json.decoder.JSONDecodeError as e:
            error_msg = "[bold red]Could not parse schema JSON:[/] {}".format(e)
            log.error(error_msg)
            raise AssertionError(error_msg)
        except AssertionError as e:
            error_msg = "[red][✗] Pipeline schema does not follow nf-core specs:\n {}".format(e)
            log.error(error_msg)
            raise AssertionError(error_msg)

    def load_schema(self):
        """Load a pipeline schema from a file"""
        with open(self.schema_filename, "r") as fh:
            self.schema = json.load(fh)
        self.schema_defaults = {}
        self.schema_params = []
        log.debug("JSON file loaded: {}".format(self.schema_filename))

    def sanitise_param_default(self, param):
        """
        Given a param, ensure that the default value is the correct variable type
        """
        if "type" not in param or "default" not in param:
            return param

        # Bools
        if param["type"] == "boolean":
            if not isinstance(param["default"], bool):
                param["default"] = param["default"] == "true"
            return param

        # For everything else, an empty string is an empty string
        if isinstance(param["default"], str) and param["default"].strip() == "":
            return ""

        # Integers
        if param["type"] == "integer":
            param["default"] = int(param["default"])
            return param

        # Numbers
        if param["type"] == "number":
            param["default"] = float(param["default"])
            return param

        # Strings
        param["default"] = str(param["default"])
        return param

    def get_schema_defaults(self):
        """
        Generate set of default input parameters from schema.

        Saves defaults to self.schema_defaults
        Returns count of how many parameters were found (with or without a default value)
        """
        # Top level schema-properties (ungrouped)
        for p_key, param in self.schema.get("properties", {}).items():
            self.schema_params.append(p_key)
            if "default" in param:
                param = self.sanitise_param_default(param)
                self.schema_defaults[p_key] = param["default"]

        # Grouped schema properties in subschema definitions
        for d_key, definition in self.schema.get("definitions", {}).items():
            for p_key, param in definition.get("properties", {}).items():
                self.schema_params.append(p_key)
                if "default" in param:
                    param = self.sanitise_param_default(param)
                    self.schema_defaults[p_key] = param["default"]

    def save_schema(self):
        """Save a pipeline schema to a file"""
        # Write results to a JSON file
        num_params = len(self.schema.get("properties", {}))
        num_params += sum([len(d.get("properties", {})) for d in self.schema.get("definitions", {}).values()])
        log.info("Writing schema with {} params: '{}'".format(num_params, self.schema_filename))
        with open(self.schema_filename, "w") as fh:
            json.dump(self.schema, fh, indent=4)

    def load_input_params(self, params_path):
        """Load a given a path to a parameters file (JSON/YAML)

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
        """Check given parameters against a schema and validate"""
        try:
            assert self.schema is not None
            jsonschema.validate(self.input_params, self.schema)
        except AssertionError:
            log.error("[red][✗] Pipeline schema not found")
            return False
        except jsonschema.exceptions.ValidationError as e:
            log.error("[red][✗] Input parameters are invalid: {}".format(e.message))
            return False
        log.info("[green][✓] Input parameters look valid")
        return True

    def validate_default_params(self):
        """
        Check that all default parameters in the schema are valid
        Ignores 'required' flag, as required parameters might have no defaults
        """
        try:
            assert self.schema is not None
            # Make copy of schema and remove required flags
            schema_no_required = copy.deepcopy(self.schema)
            if "required" in schema_no_required:
                schema_no_required.pop("required")
            for group_key, group in schema_no_required["definitions"].items():
                if "required" in group:
                    schema_no_required["definitions"][group_key].pop("required")
            jsonschema.validate(self.schema_defaults, schema_no_required)
        except AssertionError:
            log.error("[red][✗] Pipeline schema not found")
        except jsonschema.exceptions.ValidationError as e:
            raise AssertionError("Default parameters are invalid: {}".format(e.message))
        log.info("[green][✓] Default parameters look valid")

    def validate_schema(self, schema=None):
        """
        Check that the Schema is valid

        Returns: Number of parameters found
        """
        if schema is None:
            schema = self.schema
        try:
            jsonschema.Draft7Validator.check_schema(schema)
            log.debug("JSON Schema Draft7 validated")
        except jsonschema.exceptions.SchemaError as e:
            raise AssertionError("Schema does not validate as Draft 7 JSON Schema:\n {}".format(e))

        param_keys = list(schema.get("properties", {}).keys())
        num_params = len(param_keys)
        for d_key, d_schema in schema.get("definitions", {}).items():
            # Check that this definition is mentioned in allOf
            assert "allOf" in schema, "Schema has definitions, but no allOf key"
            in_allOf = False
            for allOf in schema["allOf"]:
                if allOf["$ref"] == "#/definitions/{}".format(d_key):
                    in_allOf = True
            assert in_allOf, "Definition subschema `{}` not included in schema `allOf`".format(d_key)

            for d_param_id in d_schema.get("properties", {}):
                # Check that we don't have any duplicate parameter IDs in different definitions
                assert d_param_id not in param_keys, "Duplicate parameter found in schema `definitions`: `{}`".format(
                    d_param_id
                )
                param_keys.append(d_param_id)
                num_params += 1

        # Check that everything in allOf exists
        for allOf in schema.get("allOf", []):
            assert "definitions" in schema, "Schema has allOf, but no definitions"
            def_key = allOf["$ref"][14:]
            assert def_key in schema["definitions"], "Subschema `{}` found in `allOf` but not `definitions`".format(
                def_key
            )

        # Check that the schema describes at least one parameter
        assert num_params > 0, "No parameters found in schema"

        return num_params

    def validate_schema_title_description(self, schema=None):
        """
        Extra validation command for linting.
        Checks that the schema "$id", "title" and "description" attributes match the piipeline config.
        """
        if schema is None:
            schema = self.schema
        if schema is None:
            log.debug("Pipeline schema not set - skipping validation of top-level attributes")
            return None

        assert "$schema" in self.schema, "Schema missing top-level `$schema` attribute"
        schema_attr = "http://json-schema.org/draft-07/schema"
        assert self.schema["$schema"] == schema_attr, "Schema `$schema` should be `{}`\n Found `{}`".format(
            schema_attr, self.schema["$schema"]
        )

        if self.pipeline_manifest == {}:
            self.get_wf_params()

        if "name" not in self.pipeline_manifest:
            log.debug("Pipeline manifest `name` not known - skipping validation of schema id and title")
        else:
            assert "$id" in self.schema, "Schema missing top-level `$id` attribute"
            assert "title" in self.schema, "Schema missing top-level `title` attribute"
            # Validate that id, title and description match the pipeline manifest
            id_attr = "https://raw.githubusercontent.com/{}/master/nextflow_schema.json".format(
                self.pipeline_manifest["name"].strip("\"'")
            )
            assert self.schema["$id"] == id_attr, "Schema `$id` should be `{}`\n Found `{}`".format(
                id_attr, self.schema["$id"]
            )

            title_attr = "{} pipeline parameters".format(self.pipeline_manifest["name"].strip("\"'"))
            assert self.schema["title"] == title_attr, "Schema `title` should be `{}`\n Found: `{}`".format(
                title_attr, self.schema["title"]
            )

        if "description" not in self.pipeline_manifest:
            log.debug("Pipeline manifest 'description' not known - skipping validation of schema description")
        else:
            assert "description" in self.schema, "Schema missing top-level 'description' attribute"
            desc_attr = self.pipeline_manifest["description"].strip("\"'")
            assert self.schema["description"] == desc_attr, "Schema 'description' should be '{}'\n Found: '{}'".format(
                desc_attr, self.schema["description"]
            )

    def make_skeleton_schema(self):
        """Make a new pipeline schema from the template"""
        self.schema_from_scratch = True
        # Use Jinja to render the template schema file to a variable
        env = jinja2.Environment(
            loader=jinja2.PackageLoader("nf_core", "pipeline-template"), keep_trailing_newline=True
        )
        schema_template = env.get_template("nextflow_schema.json")
        template_vars = {
            "name": self.pipeline_manifest.get("name", os.path.dirname(self.schema_filename)).strip("'"),
            "description": self.pipeline_manifest.get("description", "").strip("'"),
        }
        self.schema = json.loads(schema_template.render(template_vars))
        self.get_schema_defaults()

    def build_schema(self, pipeline_dir, no_prompts, web_only, url):
        """Interactively build a new pipeline schema for a pipeline"""

        # Check if supplied pipeline directory really is one
        try:
            nf_core.utils.is_pipeline_directory(pipeline_dir)
        except UserWarning:
            raise

        if no_prompts:
            self.no_prompts = True
        if web_only:
            self.web_only = True
        if url:
            self.web_schema_build_url = url

        # Get pipeline schema filename
        try:
            self.get_schema_path(pipeline_dir, local_only=True)
        except AssertionError:
            log.info("No existing schema found - creating a new one from the nf-core template")
            self.get_wf_params()
            self.make_skeleton_schema()
            self.remove_schema_notfound_configs()
            self.add_schema_found_configs()
            try:
                self.validate_schema()
            except AssertionError as e:
                log.error("[red]Something went wrong when building a new schema:[/] {}".format(e))
                log.info("Please ask for help on the nf-core Slack")
                return False
        else:
            # Schema found - load and validate
            try:
                self.load_lint_schema()
            except AssertionError as e:
                log.error("Existing pipeline schema found, but it is invalid: {}".format(self.schema_filename))
                log.info("Please fix or delete this file, then try again.")
                return False

        if not self.web_only:
            self.get_wf_params()
            self.remove_schema_notfound_configs()
            self.add_schema_found_configs()
            self.save_schema()

        # If running interactively, send to the web for customisation
        if not self.no_prompts:
            if Confirm.ask(":rocket:  Launch web builder for customisation and editing?"):
                try:
                    self.launch_web_builder()
                except AssertionError as e:
                    log.error(e.args[0])
                    # Extra help for people running offline
                    if "Could not connect" in e.args[0]:
                        log.info(
                            "If you're working offline, now copy your schema ({}) and paste at https://nf-co.re/pipeline_schema_builder".format(
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
        Go through top-level schema and all definitions sub-schemas to remove
        anything that's not in the nextflow config.
        """
        # Top-level properties
        self.schema, params_removed = self.remove_schema_notfound_configs_single_schema(self.schema)
        # Sub-schemas in definitions
        for d_key, definition in self.schema.get("definitions", {}).items():
            cleaned_schema, p_removed = self.remove_schema_notfound_configs_single_schema(definition)
            self.schema["definitions"][d_key] = cleaned_schema
            params_removed.extend(p_removed)
        return params_removed

    def remove_schema_notfound_configs_single_schema(self, schema):
        """
        Go through a single schema / set of properties and strip out
        anything that's not in the nextflow config.

        Takes: Schema or sub-schema with properties key
        Returns: Cleaned schema / sub-schema
        """
        # Make a deep copy so as not to edit in place
        schema = copy.deepcopy(schema)
        params_removed = []
        # Use iterator so that we can delete the key whilst iterating
        for p_key in [k for k in schema.get("properties", {}).keys()]:
            if self.prompt_remove_schema_notfound_config(p_key):
                del schema["properties"][p_key]
                # Remove required flag if set
                if p_key in schema.get("required", []):
                    schema["required"].remove(p_key)
                # Remove required list if now empty
                if "required" in schema and len(schema["required"]) == 0:
                    del schema["required"]
                log.debug("Removing '{}' from pipeline schema".format(p_key))
                params_removed.append(p_key)

        return schema, params_removed

    def prompt_remove_schema_notfound_config(self, p_key):
        """
        Check if a given key is found in the nextflow config params and prompt to remove it if note

        Returns True if it should be removed, False if not.
        """
        if p_key not in self.pipeline_params.keys():
            if self.no_prompts or self.schema_from_scratch:
                return True
            if Confirm.ask(
                ":question: Unrecognised [bold]'params.{}'[/] found in the schema but not in the pipeline config! [yellow]Remove it?".format(
                    p_key
                )
            ):
                return True
        return False

    def add_schema_found_configs(self):
        """
        Add anything that's found in the Nextflow params that's missing in the pipeline schema
        """
        params_added = []
        params_ignore = self.pipeline_params.get("schema_ignore_params", "").strip("\"'").split(",")
        params_ignore.append("schema_ignore_params")
        for p_key, p_val in self.pipeline_params.items():
            # Check if key is in schema parameters
            if p_key not in self.schema_params and p_key not in params_ignore:
                if (
                    self.no_prompts
                    or self.schema_from_scratch
                    or Confirm.ask(
                        ":sparkles: Found [bold]'params.{}'[/] in the pipeline config, but not in the schema. [blue]Add to pipeline schema?".format(
                            p_key
                        )
                    )
                ):
                    if "properties" not in self.schema:
                        self.schema["properties"] = {}
                    self.schema["properties"][p_key] = self.build_schema_param(p_val)
                    log.debug("Adding '{}' to pipeline schema".format(p_key))
                    params_added.append(p_key)

        return params_added

    def build_schema_param(self, p_val):
        """
        Build a pipeline schema dictionary for an param interactively
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

        # Anything can be "null", means that it is not set
        if p_val == "null":
            p_val = None

        # NB: Only test "True" for booleans, as it is very common to initialise
        # an empty param as false when really we expect a string at a later date..
        if p_val == "True":
            p_val = True
            p_type = "boolean"

        p_schema = {"type": p_type, "default": p_val}

        # Assume that false and empty strings shouldn't be a default
        if p_val == "false" or p_val == "" or p_val is None:
            del p_schema["default"]

        return p_schema

    def launch_web_builder(self):
        """
        Send pipeline schema to web builder and wait for response
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
            # DO NOT FIX THIS TYPO. Needs to stay in sync with the website. Maintaining for backwards compatability.
            assert web_response["status"] == "recieved"
        except (AssertionError) as e:
            log.debug("Response content:\n{}".format(json.dumps(web_response, indent=4)))
            raise AssertionError(
                "Pipeline schema builder response not recognised: {}\n See verbose log for full response (nf-core -v schema)".format(
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
            raise AssertionError("Got error from schema builder: '{}'".format(web_response.get("message")))
        elif web_response["status"] == "waiting_for_user":
            return False
        elif web_response["status"] == "web_builder_edited":
            log.info("Found saved status from nf-core schema builder")
            try:
                self.schema = web_response["schema"]
                self.validate_schema()
            except AssertionError as e:
                raise AssertionError("Response from schema builder did not pass validation:\n {}".format(e))
            else:
                self.save_schema()
                return True
        else:
            log.debug("Response content:\n{}".format(json.dumps(web_response, indent=4)))
            raise AssertionError(
                "Pipeline schema builder returned unexpected status ({}): {}\n See verbose log for full response".format(
                    web_response["status"], self.web_schema_build_api_url
                )
            )
