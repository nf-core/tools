#!/usr/bin/env python
""" Tests covering the pipeline launch code.
"""

import nf_core.launch

import json
import os
import shutil
import tempfile
import unittest

class TestLaunch(unittest.TestCase):
    """Class for schema tests"""

    def setUp(self):
        """ Create a new PipelineSchema and Launch objects """
        # Set up the schema
        root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        self.template_dir = os.path.join(root_repo_dir, 'nf_core', 'pipeline-template', '{{cookiecutter.name_noslash}}')
        self.nf_params_fn = os.path.join(tempfile.mkdtemp(), 'nf-params.json')
        self.launcher = nf_core.launch.Launch(self.template_dir, params_out = self.nf_params_fn)

    def test_get_pipeline_schema(self):
        """ Test loading the params schema from a pipeline """
        self.launcher.get_pipeline_schema()
        assert 'properties' in self.launcher.schema_obj.schema
        assert len(self.launcher.schema_obj.schema['properties']) > 2

    def test_make_pipeline_schema(self):
        """ Make a copy of the template workflow, but delete the schema file, then try to load it """
        test_pipeline_dir = os.path.join(tempfile.mkdtemp(), 'wf')
        shutil.copytree(self.template_dir, test_pipeline_dir)
        os.remove(os.path.join(test_pipeline_dir, 'nextflow_schema.json'))
        self.launcher = nf_core.launch.Launch(test_pipeline_dir, params_out = self.nf_params_fn)
        self.launcher.get_pipeline_schema()
        assert 'properties' in self.launcher.schema_obj.schema
        assert len(self.launcher.schema_obj.schema['properties']) > 2
        assert self.launcher.schema_obj.schema['properties']['Input/output options']['properties']['outdir'] == {
            'type': 'string',
            'description': 'The output directory where the results will be saved.',
            'default': './results',
            'fa_icon': 'fas fa-folder-open',
            'help_text': ''
        }

    def test_get_pipeline_defaults(self):
        """ Test fetching default inputs from the JSON schema """
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        assert len(self.launcher.schema_obj.input_params) > 0
        assert self.launcher.schema_obj.input_params['outdir'] == './results'

    def test_get_pipeline_defaults_input_params(self):
        """ Test fetching default inputs from the JSON schema with an input params file supplied """
        tmp_filehandle, tmp_filename = tempfile.mkstemp()
        with os.fdopen(tmp_filehandle, 'w') as fh:
            json.dump({'outdir': 'fubar'}, fh)
        self.launcher.params_in = tmp_filename
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        assert len(self.launcher.schema_obj.input_params) > 0
        assert self.launcher.schema_obj.input_params['outdir'] == 'fubar'

    def test_nf_merge_schema(self):
        """ Checking merging the nextflow JSON schema with the pipeline schema """
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        self.launcher.merge_nxf_flag_schema()
        assert list(self.launcher.schema_obj.schema['properties'].keys())[0] == 'Nextflow command-line flags'
        assert '-resume' in self.launcher.schema_obj.schema['properties']['Nextflow command-line flags']['properties']

    def test_ob_to_pyinquirer_string(self):
        """ Check converting a python dict to a pyenquirer format - simple strings """
        sc_obj = {
            "type": "string",
            "default": "data/*{1,2}.fastq.gz",
        }
        result = self.launcher.single_param_to_pyinquirer('reads', sc_obj)
        assert result == {
            'type': 'input',
            'name': 'reads',
            'message': 'reads',
            'default': 'data/*{1,2}.fastq.gz'
        }

    def test_ob_to_pyinquirer_bool(self):
        """ Check converting a python dict to a pyenquirer format - booleans """
        sc_obj = {
            "type": "boolean",
            "default": "True",
        }
        result = self.launcher.single_param_to_pyinquirer('single_end', sc_obj)
        assert result == {
            'type': 'confirm',
            'name': 'single_end',
            'message': 'single_end',
            'default': True
        }

    def test_ob_to_pyinquirer_number(self):
        """ Check converting a python dict to a pyenquirer format - with enum """
        sc_obj = {
            "type": "number",
            "default": 0.1
        }
        result = self.launcher.single_param_to_pyinquirer('min_reps_consensus', sc_obj)
        assert result['type'] == 'input'
        assert result['default'] == '0.1'
        assert result['validate']('123')
        assert result['validate']('-123.56')
        assert result['validate']('')
        assert result['validate']('123.56.78') == 'Must be a number'
        assert result['validate']('123.56sdkfjb') == 'Must be a number'

    def test_ob_to_pyinquirer_integer(self):
        """ Check converting a python dict to a pyenquirer format - with enum """
        sc_obj = {
            "type": "integer",
            "default": 1
        }
        result = self.launcher.single_param_to_pyinquirer('broad_cutoff', sc_obj)
        assert result['type'] == 'input'
        assert result['default'] == '1'
        assert result['validate']('123')
        assert result['validate']('-123')
        assert result['validate']('')
        assert result['validate']('123.45') == 'Must be an integer'
        assert result['validate']('123.56sdkfjb') == 'Must be an integer'

    def test_ob_to_pyinquirer_range(self):
        """ Check converting a python dict to a pyenquirer format - with enum """
        sc_obj = {
            "type": "range",
            "minimum": "10",
            "maximum": "20",
            "default": 15
        }
        result = self.launcher.single_param_to_pyinquirer('broad_cutoff', sc_obj)
        assert result['type'] == 'input'
        assert result['default'] == '15'
        assert result['validate']('20')
        assert result['validate']('')
        assert result['validate']('123.56sdkfjb') == 'Must be a number'
        assert result['validate']('8') == 'Must be greater than or equal to 10'
        assert result['validate']('25') == 'Must be less than or equal to 20'

    def test_ob_to_pyinquirer_enum(self):
        """ Check converting a python dict to a pyenquirer format - with enum """
        sc_obj = {
            "type": "string",
            "default": "copy",
            "enum": [ "symlink", "rellink" ]
        }
        result = self.launcher.single_param_to_pyinquirer('publish_dir_mode', sc_obj)
        assert result['type'] == 'input'
        assert result['default'] == 'copy'
        assert result['validate']('symlink')
        assert result['validate']('')
        assert result['validate']('not_allowed') == 'Must be one of: symlink, rellink'

    def test_ob_to_pyinquirer_pattern(self):
        """ Check converting a python dict to a pyenquirer format - with pattern """
        sc_obj = {
            "type": "string",
            "pattern": "^([a-zA-Z0-9_\\-\\.]+)@([a-zA-Z0-9_\\-\\.]+)\\.([a-zA-Z]{2,5})$"
        }
        result = self.launcher.single_param_to_pyinquirer('email', sc_obj)
        assert result['type'] == 'input'
        assert result['validate']('test@email.com')
        assert result['validate']('')
        assert result['validate']('not_an_email') == 'Must match pattern: ^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,5})$'

    def test_strip_default_params(self):
        """ Test stripping default parameters """
        self.launcher.get_pipeline_schema()
        self.launcher.set_schema_inputs()
        self.launcher.schema_obj.input_params.update({'reads': 'custom_input'})
        assert len(self.launcher.schema_obj.input_params) > 1
        self.launcher.strip_default_params()
        assert self.launcher.schema_obj.input_params == {'reads': 'custom_input'}

    def test_build_command_empty(self):
        """ Test the functionality to build a nextflow command - nothing customsied """
        self.launcher.get_pipeline_schema()
        self.launcher.merge_nxf_flag_schema()
        self.launcher.build_command()
        assert self.launcher.nextflow_cmd == 'nextflow run {}'.format(self.template_dir)

    def test_build_command_nf(self):
        """ Test the functionality to build a nextflow command - core nf customised """
        self.launcher.get_pipeline_schema()
        self.launcher.merge_nxf_flag_schema()
        self.launcher.nxf_flags['-name'] = 'Test_Workflow'
        self.launcher.nxf_flags['-resume'] = True
        self.launcher.build_command()
        assert self.launcher.nextflow_cmd == 'nextflow run {} -name "Test_Workflow" -resume'.format(self.template_dir)

    def test_build_command_params(self):
        """ Test the functionality to build a nextflow command - params supplied """
        self.launcher.get_pipeline_schema()
        self.launcher.schema_obj.input_params.update({'reads': 'custom_input'})
        self.launcher.build_command()
        # Check command
        assert self.launcher.nextflow_cmd == 'nextflow run {} -params-file "{}"'.format(self.template_dir, os.path.relpath(self.nf_params_fn))
        # Check saved parameters file
        with open(self.nf_params_fn, 'r') as fh:
            saved_json = json.load(fh)
        assert saved_json == {'reads': 'custom_input'}

    def test_build_command_params_cl(self):
        """ Test the functionality to build a nextflow command - params on Nextflow command line """
        self.launcher.use_params_file = False
        self.launcher.get_pipeline_schema()
        self.launcher.schema_obj.input_params.update({'reads': 'custom_input'})
        self.launcher.build_command()
        assert self.launcher.nextflow_cmd == 'nextflow run {} --reads "custom_input"'.format(self.template_dir)
