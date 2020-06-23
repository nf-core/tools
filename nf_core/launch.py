#!/usr/bin/env python
""" Launch a pipeline, interactively collecting params """

from __future__ import print_function

import click
import copy
import json
import logging
import os
import PyInquirer
import re
import subprocess
import textwrap

import nf_core.schema

# TODO: Would be nice to be able to capture keyboard interruptions in a nicer way
# add raise_keyboard_interrupt=True argument to PyInquirer.prompt() calls
# Requires a new release of PyInquirer. See https://github.com/CITGuru/PyInquirer/issues/90

def launch_pipeline(pipeline, command_only, params_in=None, params_out=None, save_all=False, show_hidden=False):

    logging.info("This tool ignores any pipeline parameter defaults overwritten by Nextflow config files or profiles\n")

    # Create a pipeline launch object
    launcher = Launch(pipeline, command_only, params_in, params_out, show_hidden)

    # Build the schema and starting inputs
    if launcher.get_pipeline_schema() is False:
        return False
    launcher.set_schema_inputs()
    launcher.merge_nxf_flag_schema()

    # Kick off the interactive wizard to collect user inputs
    launcher.prompt_schema()

    # Validate the parameters that we now have
    if not launcher.schema_obj.validate_params():
        return False

    # Strip out the defaults
    if not save_all:
        launcher.strip_default_params()

    # Build and launch the `nextflow run` command
    launcher.build_command()
    launcher.launch_workflow()

class Launch(object):
    """ Class to hold config option to launch a pipeline """

    def __init__(self, pipeline, command_only=False, params_in=None, params_out=None, show_hidden=False):
        """Initialise the Launcher class

        Args:
          schema: An nf_core.schema.PipelineSchema() object
        """

        self.pipeline = pipeline
        self.schema_obj = None
        self.use_params_file = True
        if command_only:
            self.use_params_file = False
        self.params_in = params_in
        if params_out:
            self.params_out = params_out
        else:
            self.params_out = os.path.join(os.getcwd(), 'nf-params.json')
        self.show_hidden = False
        if show_hidden:
            self.show_hidden = True

        self.nextflow_cmd = 'nextflow run {}'.format(self.pipeline)

        # Prepend property names with a single hyphen in case we have parameters with the same ID
        self.nxf_flag_schema = {
            'Nextflow command-line flags': {
                'type': 'object',
                'description': 'General Nextflow flags to control how the pipeline runs.',
                'help_text': """
                    These are not specific to the pipeline and will not be saved
                    in any parameter file. They are just used when building the
                    `nextflow run` launch command.
                """,
                'properties': {
                    '-name': {
                        'type': 'string',
                        'description': 'Unique name for this nextflow run',
                        'pattern': '^[a-zA-Z0-9-_]$'
                    },
                    '-revision': {
                        'type': 'string',
                        'description': 'Pipeline release / branch to use',
                        'help_text': 'Revision of the project to run (either a git branch, tag or commit SHA number)'
                    },
                    '-profile': {
                        'type': 'string',
                        'description': 'Configuration profile'
                    },
                    '-work-dir': {
                        'type': 'string',
                        'description': 'Work directory for intermediate files',
                        'default': os.getenv('NXF_WORK') if os.getenv('NXF_WORK') else './work',
                    },
                    '-resume': {
                        'type': 'boolean',
                        'description': 'Resume previous run, if found',
                        'help_text': """
                            Execute the script using the cached results, useful to continue
                            executions that was stopped by an error
                        """,
                        'default': False
                    }
                }
            }
        }
        self.nxf_flags = {}
        self.params_user = {}

    def get_pipeline_schema(self):
        """ Load and validate the schema from the supplied pipeline """

        # Get the schema
        self.schema_obj = nf_core.schema.PipelineSchema()
        try:
            # Get schema from name, load it and lint it
            self.schema_obj.lint_schema(self.pipeline)
        except AssertionError:
            # No schema found, just scrape the pipeline for parameters
            logging.info("No pipeline schema found - creating one from the config")
            try:
                self.schema_obj.get_wf_params()
                self.schema_obj.make_skeleton_schema()
                self.schema_obj.remove_schema_notfound_configs()
                self.schema_obj.add_schema_found_configs()
                self.schema_obj.flatten_schema()
                self.schema_obj.get_schema_defaults()
            except AssertionError as e:
                logging.error("Could not build pipeline schema: {}".format(e))
                return False

    def set_schema_inputs(self):
        """
        Take the loaded schema and set the defaults as the input parameters
        If a nf_params.json file is supplied, apply these over the top
        """
        # Set the inputs to the schema defaults
        self.schema_obj.input_params = copy.deepcopy(self.schema_obj.schema_defaults)

        # If we have a params_file, load and validate it against the schema
        if self.params_in:
            logging.info("Loading {}".format(self.params_in))
            self.schema_obj.load_input_params(self.params_in)
            self.schema_obj.validate_params()

    def merge_nxf_flag_schema(self):
        """ Take the Nextflow flag schema and merge it with the pipeline schema """
        # Do it like this so that the Nextflow params come first
        schema_params = self.nxf_flag_schema
        schema_params.update(self.schema_obj.schema['properties'])
        self.schema_obj.schema['properties'] = schema_params


    def prompt_schema(self):
        """ Go through the pipeline schema and prompt user to change defaults """
        answers = {}
        for param_id, param_obj in self.schema_obj.schema['properties'].items():
            if(param_obj['type'] == 'object'):
                if not param_obj.get('hidden', False) or self.show_hidden:
                    answers.update(self.prompt_group(param_id, param_obj))
            else:
                if not param_obj.get('hidden', False) or self.show_hidden:
                    is_required = param_id in self.schema_obj.schema.get('required', [])
                    answers.update(self.prompt_param(param_id, param_obj, is_required, answers))

        # Split answers into core nextflow options and params
        for key, answer in answers.items():
            if key == 'Nextflow command-line flags':
                continue
            elif key in self.nxf_flag_schema['Nextflow command-line flags']['properties']:
                self.nxf_flags[key] = answer
            else:
                self.params_user[key] = answer

        # Update schema with user params
        self.schema_obj.input_params.update(self.params_user)

    def prompt_param(self, param_id, param_obj, is_required, answers):
        """Prompt for a single parameter"""

        # Print the question
        question = self.single_param_to_pyinquirer(param_id, param_obj, answers)
        answer = PyInquirer.prompt([question])

        # If got ? then print help and ask again
        while answer[param_id] == '?':
            if 'help_text' in param_obj:
                click.secho("\n{}\n".format(param_obj['help_text']), dim=True, err=True)
            answer = PyInquirer.prompt([question])

        # If required and got an empty reponse, ask again
        while type(answer[param_id]) is str and answer[param_id].strip() == '' and is_required:
            click.secho("Error - this property is required.", fg='red', err=True)
            answer = PyInquirer.prompt([question])

        # Don't return empty answers
        if answer[param_id] == '':
            return {}
        return answer

    def prompt_group(self, param_id, param_obj):
        """Prompt for edits to a group of parameters
        Only works for single-level groups (no nested!)

        Args:
          param_id: Paramater ID (string)
          param_obj: JSON Schema keys - no objects (dict)

        Returns:
          Dict of param_id:val answers
        """
        question = {
            'type': 'list',
            'name': param_id,
            'message': param_id,
            'choices': [
                'Continue >>',
                PyInquirer.Separator()
            ]
        }

        for child_param, child_param_obj in param_obj['properties'].items():
            if(child_param_obj['type'] == 'object'):
                logging.error("nf-core only supports groups 1-level deep")
                return {}
            else:
                if not child_param_obj.get('hidden', False) or self.show_hidden:
                    question['choices'].append(child_param)

        # Skip if all questions hidden
        if len(question['choices']) == 2:
            return {}

        while_break = False
        answers = {}
        while not while_break:
            self.print_param_header(param_id, param_obj)
            answer = PyInquirer.prompt([question])
            if answer[param_id] == 'Continue >>':
                while_break = True
            else:
                child_param = answer[param_id]
                is_required = child_param in param_obj.get('required', [])
                answers.update(self.prompt_param(child_param, param_obj['properties'][child_param], is_required, answers))

        return answers

    def single_param_to_pyinquirer(self, param_id, param_obj, answers):
        """Convert a JSONSchema param to a PyInquirer question

        Args:
          param_id: Paramater ID (string)
          param_obj: JSON Schema keys - no objects (dict)

        Returns:
          Single PyInquirer dict, to be appended to questions list
        """
        question = {
            'type': 'input',
            'name': param_id,
            'message': param_id
        }

        # Print the name, description & help text
        nice_param_id = '--{}'.format(param_id) if not param_id.startswith('-') else param_id
        self.print_param_header(nice_param_id, param_obj)

        if param_obj.get('type') == 'boolean':
            question['type'] = 'confirm'
            question['default'] = False

        # Default value from parsed schema, with --params-in etc
        if param_id in self.schema_obj.input_params:
            if param_obj['type'] == 'boolean' and type(self.schema_obj.input_params[param_id]) is str:
                question['default'] = 'true' == self.schema_obj.input_params[param_id].lower()
            else:
                question['default'] = self.schema_obj.input_params[param_id]

        # Overwrite if already had an answer
        if param_id in answers:
            question['default'] = answers[param_id]

        # Coerce default to a string if not boolean
        if param_obj.get('type') != 'boolean':
            question['default'] = str(question['default'])

        # Validate number type
        if param_obj.get('type') == 'number':
            def validate_number(val):
                try:
                    float(val)
                except (ValueError):
                    return "Must be a number"
                else:
                    return True
            question['validate'] = validate_number

        # Validate integer type
        if param_obj.get('type') == 'integer':
            def validate_integer(val):
                try:
                    assert int(val) == float(val)
                except (AssertionError, ValueError):
                    return "Must be an integer"
                else:
                    return True
            question['validate'] = validate_integer

        # Validate range type
        if param_obj.get('type') == 'range':
            def validate_range(val):
                try:
                    fval = float(val)
                    assert str(fval) == str(val)
                    if 'minimum' in param_obj and fval < param_obj['minimum']:
                        return "Must be greater than or equal to {}".format(float(param_obj['minimum']))
                    if 'maximum' in param_obj and fval > param_obj['maximum']:
                        return "Must be less than or equal to {}".format(float(param_obj['maximum']))
                    return True
                except (AssertionError, ValueError):
                    return "Must be a number"
            question['validate'] = validate_range

        # Validate enum from schema
        if 'enum' in param_obj:
            def validate_enum(val):
                if val == '':
                    return True
                if val in param_obj['enum']:
                    return True
                return "Must be one of: {}".format(", ".join(param_obj['enum']))
            question['validate'] = validate_enum

        # Validate pattern from schema
        if 'pattern' in param_obj:
            def validate_pattern(val):
                if val == '':
                    return True
                if re.search(param_obj['pattern'], val) is not None:
                    return True
                return "Must match pattern: {}".format(param_obj['pattern'])
            question['validate'] = validate_pattern

        return question

    def print_param_header(self, param_id, param_obj):
        if 'description' not in param_obj and 'help_text' not in param_obj:
            return
        header_str = click.style(param_id, bold=True)
        if 'description' in param_obj:
            header_str += ' - {}'.format(param_obj['description'])
        if 'help_text' in param_obj:
            # Strip indented and trailing whitespace
            help_text = textwrap.dedent(param_obj['help_text']).strip()
            # Replace single newlines, leave double newlines in place
            help_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', help_text)
            header_str += "\n" + click.style(help_text, dim=True)
        click.echo("\n"+header_str, err=True)

    def strip_default_params(self):
        """ Strip parameters if they have not changed from the default """

        for param_id, val in self.schema_obj.schema_defaults.items():
            if self.schema_obj.input_params[param_id] == val:
                del self.schema_obj.input_params[param_id]

    def build_command(self):
        """ Build the nextflow run command based on what we know """

        # Core nextflow options
        for flag, val in self.nxf_flags.items():
            # Boolean flags like -resume
            if isinstance(val, bool) and val:
                self.nextflow_cmd += " {}".format(flag)
            # String values
            else:
                self.nextflow_cmd += ' {} "{}"'.format(flag, val.replace('"', '\\"'))

        # Pipeline parameters
        if len(self.schema_obj.input_params) > 0:

            # Write the user selection to a file and run nextflow with that
            if self.use_params_file:
                with open(self.params_out, "w") as fp:
                    json.dump(self.schema_obj.input_params, fp, indent=4)
                self.nextflow_cmd += ' {} "{}"'.format("-params-file", os.path.relpath(self.params_out))

            # Call nextflow with a list of command line flags
            else:
                for param, val in self.schema_obj.input_params.items():
                    # Boolean flags like --saveTrimmed
                    if isinstance(val, bool) and val:
                        self.nextflow_cmd += " --{}".format(param)
                    # everything else
                    else:
                        self.nextflow_cmd += ' --{} "{}"'.format(param, val.replace('"', '\\"'))


    def launch_workflow(self):
        """ Launch nextflow if required  """
        intro = click.style("Nextflow command:", bold=True, underline=True)
        cmd = click.style(self.nextflow_cmd, fg='magenta')
        logging.info("{}\n  {}\n\n".format(intro, cmd))

        if click.confirm('Do you want to run this command now? '+click.style('[y/N]', fg='green'), default=False, show_default=False):
            logging.info("Launching workflow!")
            subprocess.call(self.nextflow_cmd, shell=True)
