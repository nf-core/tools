#!/usr/bin/env python
""" Tests covering the pipeline launch code.
"""

import nf_core.launch

import json
import mock
import os
import shutil
import tempfile
import unittest

from .utils import with_temporary_folder, with_temporary_file


class TestLaunch(unittest.TestCase):
    """Class for launch tests"""

    def setUp(self):
        """Create a new PipelineSchema and Launch objects"""
        # Set up the schema
        root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(root_repo_dir, "nf_core", "pipeline-template")
        # cannot use a context manager here, since outside setUp the temporary
        # file will never exists
        self.tmp_dir = tempfile.mkdtemp()
        self.nf_params_fn = os.path.join(self.tmp_dir, "nf-params.json")
        self.launcher = nf_core.launch.Launch(self.template_dir, params_out=self.nf_params_fn)

    def tearDown(self):
        """Clean up temporary files and folders"""

        if os.path.exists(self.nf_params_fn):
            os.remove(self.nf_params_fn)

        if os.path.exists(self.tmp_dir):
            os.rmdir(self.tmp_dir)

    @mock.patch.object(nf_core.launch.Launch, "prompt_web_gui", side_effect=[True])
    @mock.patch.object(nf_core.launch.Launch, "launch_web_gui")
    def test_launch_pipeline(self, mock_webbrowser, mock_lauch_web_gui):
        """Test the main launch function"""
        self.launcher.launch_pipeline()

    @mock.patch.object(nf_core.launch.Confirm, "ask", side_effect=[False])
    def test_launch_file_exists(self, mock_confirm):
        """Test that we detect an existing params file and return"""
        # Make an empty params file to be overwritten
        open(self.nf_params_fn, "a").close()
        # Try and to launch, return with error
        assert self.launcher.launch_pipeline() is False

    @mock.patch.object(nf_core.launch.Launch, "prompt_web_gui", side_effect=[True])
    @mock.patch.object(nf_core.launch.Launch, "launch_web_gui")
    @mock.patch.object(nf_core.launch.Confirm, "ask", side_effect=[False])
    def test_launch_file_exists_overwrite(self, mock_webbrowser, mock_lauch_web_gui, mock_confirm):
        """Test that we detect an existing params file and we overwrite it"""
        # Make an empty params file to be overwritten
        open(self.nf_params_fn, "a").close()
        # Try and to launch, return with error
        self.launcher.launch_pipeline()

    def test_get_pipeline_schema(self):
        """Test loading the params schema from a pipeline"""
        self.launcher.get_pipeline_schema()
        assert len(self.launcher.schema_obj.schema["definitions"]["input_output_options"]["properties"]) > 2

    @with_temporary_folder
    def test_make_pipeline_schema(self, tmp_path):
        """Make a copy of the template workflow, but delete the schema file, then try to load it"""
        test_pipeline_dir = os.path.join(tmp_path, "wf")
        shutil.copytree(self.template_dir, test_pipeline_dir)
        os.remove(os.path.join(test_pipeline_dir, "nextflow_schema.json"))
        self.launcher = nf_core.launch.Launch(test_pipeline_dir, params_out=self.nf_params_fn)
        self.launcher.get_pipeline_schema()
        assert len(self.launcher.schema_obj.schema["definitions"]["input_output_options"]["properties"]) > 2
        assert self.launcher.schema_obj.schema["definitions"]["input_output_options"]["properties"]["outdir"] == {
            "type": "string",
            "format": "directory-path",
            "description": "The output directory where the results will be saved. You have to use absolute paths to storage on Cloud infrastructure.",
            "fa_icon": "fas fa-folder-open",
        }

    def test_get_pipeline_defaults(self):
        """Test fetching default inputs from the pipeline schema"""
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        assert len(self.launcher.schema_obj.input_params) > 0
        assert self.launcher.schema_obj.input_params["validate_params"] == True

    @with_temporary_file
    def test_get_pipeline_defaults_input_params(self, tmp_file):
        """Test fetching default inputs from the pipeline schema with an input params file supplied"""
        with open(tmp_file.name, "w") as fh:
            json.dump({"outdir": "fubar"}, fh)
        self.launcher.params_in = tmp_file.name
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        assert len(self.launcher.schema_obj.input_params) > 0
        assert self.launcher.schema_obj.input_params["outdir"] == "fubar"

    def test_nf_merge_schema(self):
        """Checking merging the nextflow schema with the pipeline schema"""
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        self.launcher.merge_nxf_flag_schema()
        assert self.launcher.schema_obj.schema["allOf"][0] == {"$ref": "#/definitions/coreNextflow"}
        assert "-resume" in self.launcher.schema_obj.schema["definitions"]["coreNextflow"]["properties"]

    def test_ob_to_questionary_string(self):
        """Check converting a python dict to a pyenquirer format - simple strings"""
        sc_obj = {
            "type": "string",
            "default": "data/*{1,2}.fastq.gz",
        }
        result = self.launcher.single_param_to_questionary("input", sc_obj)
        assert result == {"type": "input", "name": "input", "message": "", "default": "data/*{1,2}.fastq.gz"}

    @mock.patch("questionary.unsafe_prompt", side_effect=[{"use_web_gui": "Web based"}])
    def test_prompt_web_gui_true(self, mock_prompt):
        """Check the prompt to launch the web schema or use the cli"""
        assert self.launcher.prompt_web_gui() == True

    @mock.patch("questionary.unsafe_prompt", side_effect=[{"use_web_gui": "Command line"}])
    def test_prompt_web_gui_false(self, mock_prompt):
        """Check the prompt to launch the web schema or use the cli"""
        assert self.launcher.prompt_web_gui() == False

    @mock.patch("nf_core.utils.poll_nfcore_web_api", side_effect=[{}])
    def test_launch_web_gui_missing_keys(self, mock_poll_nfcore_web_api):
        """Check the code that opens the web browser"""
        self.launcher.get_pipeline_schema()
        self.launcher.merge_nxf_flag_schema()
        try:
            self.launcher.launch_web_gui()
            raise UserWarning("Should have hit an AssertionError")
        except AssertionError as e:
            assert e.args[0].startswith("Web launch response not recognised:")

    @mock.patch(
        "nf_core.utils.poll_nfcore_web_api", side_effect=[{"api_url": "foo", "web_url": "bar", "status": "recieved"}]
    )
    @mock.patch("webbrowser.open")
    @mock.patch("nf_core.utils.wait_cli_function")
    def test_launch_web_gui(self, mock_poll_nfcore_web_api, mock_webbrowser, mock_wait_cli_function):
        """Check the code that opens the web browser"""
        self.launcher.get_pipeline_schema()
        self.launcher.merge_nxf_flag_schema()
        assert self.launcher.launch_web_gui() == None

    @mock.patch("nf_core.utils.poll_nfcore_web_api", side_effect=[{"status": "error", "message": "foo"}])
    def test_get_web_launch_response_error(self, mock_poll_nfcore_web_api):
        """Test polling the website for a launch response - status error"""
        try:
            self.launcher.get_web_launch_response()
            raise UserWarning("Should have hit an AssertionError")
        except AssertionError as e:
            assert e.args[0] == "Got error from launch API (foo)"

    @mock.patch("nf_core.utils.poll_nfcore_web_api", side_effect=[{"status": "foo"}])
    def test_get_web_launch_response_unexpected(self, mock_poll_nfcore_web_api):
        """Test polling the website for a launch response - status error"""
        try:
            self.launcher.get_web_launch_response()
            raise UserWarning("Should have hit an AssertionError")
        except AssertionError as e:
            assert e.args[0].startswith("Web launch GUI returned unexpected status (foo): ")

    @mock.patch("nf_core.utils.poll_nfcore_web_api", side_effect=[{"status": "waiting_for_user"}])
    def test_get_web_launch_response_waiting(self, mock_poll_nfcore_web_api):
        """Test polling the website for a launch response - status waiting_for_user"""
        assert self.launcher.get_web_launch_response() == False

    @mock.patch("nf_core.utils.poll_nfcore_web_api", side_effect=[{"status": "launch_params_complete"}])
    def test_get_web_launch_response_missing_keys(self, mock_poll_nfcore_web_api):
        """Test polling the website for a launch response - complete, but missing keys"""
        try:
            self.launcher.get_web_launch_response()
            raise UserWarning("Should have hit an AssertionError")
        except AssertionError as e:
            assert e.args[0] == "Missing return key from web API: 'nxf_flags'"

    @mock.patch(
        "nf_core.utils.poll_nfcore_web_api",
        side_effect=[
            {
                "status": "launch_params_complete",
                "nxf_flags": {"resume", "true"},
                "input_params": {"foo", "bar"},
                "schema": {},
                "cli_launch": True,
                "nextflow_cmd": "nextflow run foo",
                "pipeline": "foo",
                "revision": "bar",
            }
        ],
    )
    @mock.patch.object(nf_core.launch.Launch, "sanitise_web_response")
    def test_get_web_launch_response_valid(self, mock_poll_nfcore_web_api, mock_sanitise):
        """Test polling the website for a launch response - complete, valid response"""
        self.launcher.get_pipeline_schema()
        assert self.launcher.get_web_launch_response() == True

    def test_sanitise_web_response(self):
        """Check that we can properly sanitise results from the web"""
        self.launcher.get_pipeline_schema()
        self.launcher.nxf_flags["-name"] = ""
        self.launcher.schema_obj.input_params["igenomes_ignore"] = "true"
        self.launcher.schema_obj.input_params["max_cpus"] = "12"
        self.launcher.sanitise_web_response()
        assert "-name" not in self.launcher.nxf_flags
        assert self.launcher.schema_obj.input_params["igenomes_ignore"] == True
        assert self.launcher.schema_obj.input_params["max_cpus"] == 12

    def test_ob_to_questionary_bool(self):
        """Check converting a python dict to a pyenquirer format - booleans"""
        sc_obj = {
            "type": "boolean",
            "default": "True",
        }
        result = self.launcher.single_param_to_questionary("single_end", sc_obj)
        assert result["type"] == "list"
        assert result["name"] == "single_end"
        assert result["message"] == ""
        assert result["choices"] == ["True", "False"]
        assert result["default"] == "True"
        print(type(True))
        assert result["filter"]("True") == True
        assert result["filter"]("true") == True
        assert result["filter"](True) == True
        assert result["filter"]("False") == False
        assert result["filter"]("false") == False
        assert result["filter"](False) == False

    def test_ob_to_questionary_number(self):
        """Check converting a python dict to a pyenquirer format - with enum"""
        sc_obj = {"type": "number", "default": 0.1}
        result = self.launcher.single_param_to_questionary("min_reps_consensus", sc_obj)
        assert result["type"] == "input"
        assert result["default"] == "0.1"
        assert result["validate"]("123") is True
        assert result["validate"]("-123.56") is True
        assert result["validate"]("") is True
        assert result["validate"]("123.56.78") == "Must be a number"
        assert result["validate"]("123.56sdkfjb") == "Must be a number"
        assert result["filter"]("123.456") == float(123.456)
        assert result["filter"]("") == ""

    def test_ob_to_questionary_integer(self):
        """Check converting a python dict to a pyenquirer format - with enum"""
        sc_obj = {"type": "integer", "default": 1}
        result = self.launcher.single_param_to_questionary("broad_cutoff", sc_obj)
        assert result["type"] == "input"
        assert result["default"] == "1"
        assert result["validate"]("123") is True
        assert result["validate"]("-123") is True
        assert result["validate"]("") is True
        assert result["validate"]("123.45") == "Must be an integer"
        assert result["validate"]("123.56sdkfjb") == "Must be an integer"
        assert result["filter"]("123") == int(123)
        assert result["filter"]("") == ""

    def test_ob_to_questionary_range(self):
        """Check converting a python dict to a pyenquirer format - with enum"""
        sc_obj = {"type": "number", "minimum": "10", "maximum": "20", "default": 15}
        result = self.launcher.single_param_to_questionary("broad_cutoff", sc_obj)
        assert result["type"] == "input"
        assert result["default"] == "15"
        assert result["validate"]("20") is True
        assert result["validate"]("") is True
        assert result["validate"]("123.56sdkfjb") == "Must be a number"
        assert result["validate"]("8") == "Must be greater than or equal to 10"
        assert result["validate"]("25") == "Must be less than or equal to 20"
        assert result["filter"]("20") == float(20)
        assert result["filter"]("") == ""

    def test_ob_to_questionary_enum(self):
        """Check converting a python dict to a questionary format - with enum"""
        sc_obj = {"type": "string", "default": "copy", "enum": ["symlink", "rellink"]}
        result = self.launcher.single_param_to_questionary("publish_dir_mode", sc_obj)
        assert result["type"] == "list"
        assert result["default"] == "copy"
        assert result["choices"] == ["symlink", "rellink"]

    def test_ob_to_questionary_pattern(self):
        """Check converting a python dict to a questionary format - with pattern"""
        sc_obj = {"type": "string", "pattern": "^([a-zA-Z0-9_\\-\\.]+)@([a-zA-Z0-9_\\-\\.]+)\\.([a-zA-Z]{2,5})$"}
        result = self.launcher.single_param_to_questionary("email", sc_obj)
        assert result["type"] == "input"
        assert result["validate"]("test@email.com") is True
        assert result["validate"]("") is True
        assert (
            result["validate"]("not_an_email")
            == r"Must match pattern: ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$"
        )

    def test_strip_default_params(self):
        """Test stripping default parameters"""
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        self.launcher.schema_obj.input_params.update({"input": "custom_input"})
        assert len(self.launcher.schema_obj.input_params) > 1
        self.launcher.strip_default_params()
        assert self.launcher.schema_obj.input_params == {"input": "custom_input"}

    def test_build_command_empty(self):
        """Test the functionality to build a nextflow command - nothing customsied"""
        self.launcher.get_pipeline_schema()
        self.launcher.merge_nxf_flag_schema()
        self.launcher.build_command()
        assert self.launcher.nextflow_cmd == "nextflow run {}".format(self.template_dir)

    def test_build_command_nf(self):
        """Test the functionality to build a nextflow command - core nf customised"""
        self.launcher.get_pipeline_schema()
        self.launcher.merge_nxf_flag_schema()
        self.launcher.nxf_flags["-name"] = "Test_Workflow"
        self.launcher.nxf_flags["-resume"] = True
        self.launcher.build_command()
        assert self.launcher.nextflow_cmd == 'nextflow run {} -name "Test_Workflow" -resume'.format(self.template_dir)

    def test_build_command_params(self):
        """Test the functionality to build a nextflow command - params supplied"""
        self.launcher.get_pipeline_schema()
        self.launcher.schema_obj.input_params.update({"input": "custom_input"})
        self.launcher.build_command()
        # Check command
        assert self.launcher.nextflow_cmd == 'nextflow run {} -params-file "{}"'.format(
            self.template_dir, os.path.relpath(self.nf_params_fn)
        )
        # Check saved parameters file
        with open(self.nf_params_fn, "r") as fh:
            saved_json = json.load(fh)
        assert saved_json == {"input": "custom_input"}

    def test_build_command_params_cl(self):
        """Test the functionality to build a nextflow command - params on Nextflow command line"""
        self.launcher.use_params_file = False
        self.launcher.get_pipeline_schema()
        self.launcher.schema_obj.input_params.update({"input": "custom_input"})
        self.launcher.build_command()
        assert self.launcher.nextflow_cmd == 'nextflow run {} --input "custom_input"'.format(self.template_dir)
