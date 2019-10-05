#!/usr/bin/env python
""" Launch a pipeline, interactively collecting params """

from __future__ import print_function
from collections import OrderedDict

import click
import errno
import jsonschema
import logging
import os
import re
import subprocess

import nf_core.utils, nf_core.list
import nf_core.workflow.parameters, nf_core.workflow.validation, nf_core.workflow.workflow

def launch_pipeline(workflow, params_local_uri, direct):

    # Create a pipeline launch object
    launcher = Launch(workflow)

    # Get nextflow to fetch the workflow if we don't already have it
    if not launcher.wf_ispath:
        launcher.get_local_wf()

    # Get the pipeline default parameters
    launcher.parse_parameter_settings(params_local_uri)

    # Find extra params from `nextflow config` command and main.nf
    launcher.collect_pipeline_param_defaults()

    # Group the parameters
    launcher.group_parameters()

    # Kick off the interactive wizard to collect user inputs
    launcher.prompt_core_nxf_flags()
    if not direct:
        launcher.prompt_param_flags()

    # Build and launch the `nextflow run` command
    launcher.build_command()
    launcher.launch_workflow()

class Launch(object):
    """ Class to hold config option to launch a pipeline """

    def __init__(self, workflow):
        """ Initialise the class with empty placeholder vars """

        # Check if the workflow name is actually a path
        self.wf_ispath = os.path.exists(workflow)

        # Prepend nf-core/ if it seems sensible
        if 'nf-core' not in workflow and workflow.count('/') == 0 and not self.wf_ispath:
            workflow = "nf-core/{}".format(workflow)
            logging.debug("Prepending nf-core/ to workflow")
        logging.info("Launching {}".format(workflow))

        # Get list of local workflows to see if we have a cached version
        self.local_wf = None
        if not self.wf_ispath:
            wfs = nf_core.list.Workflows()
            wfs.get_local_nf_workflows()
            for wf in wfs.local_workflows:
                if workflow == wf.full_name:
                    self.local_wf = wf

        self.workflow = workflow
        self.nxf_flag_defaults = {
            '-name': None,
            '-r': None,
            '-profile': 'standard',
            '-w': os.getenv('NXF_WORK') if os.getenv('NXF_WORK') else './work',
            '-resume': False
        }
        self.nxf_flag_help = {
            '-name': 'Unique name for this nextflow run',
            '-r': 'Release / revision to use',
            '-profile': 'Config profile to use',
            '-w': 'Work directory for intermediate files',
            '-resume': 'Resume a previous workflow run'
        }
        self.nxf_flags = {}
        self.parameters = []
        self.parameter_keys = []
        self.grouped_parameters = OrderedDict()
        self.params_user = {}
        self.nextflow_cmd = "nextflow run {}".format(self.workflow)
        self.use_params_file = True

    def get_local_wf(self):
        """
        Check if this workflow has a local copy and use nextflow to pull it if not
        """
        if not self.local_wf:
            logging.info("Downloading workflow: {}".format(self.workflow))
            try:
                with open(os.devnull, 'w') as devnull:
                    subprocess.check_output(['nextflow', 'pull', self.workflow], stderr=devnull)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
            except subprocess.CalledProcessError as e:
                raise AssertionError("`nextflow pull` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
            else:
                self.local_wf = nf_core.list.LocalWorkflow(self.workflow)
                self.local_wf.get_local_nf_workflow_details()

    def parse_parameter_settings(self, params_local_uri = None):
        """
        Load full parameter info from the pipeline parameters.settings.json file
        """
        try:
            params_json_str = None
            # Params file supplied to launch command
            if params_local_uri:
                with open(params_local_uri, 'r') as fp:
                    params_json_str = fp.read()
            # Get workflow file from local cached copy
            else:
                if self.wf_ispath:
                    local_params_path = os.path.join(self.workflow, 'parameters.settings.json')
                else:
                    local_params_path = os.path.join(self.local_wf.local_path, 'parameters.settings.json')
                if os.path.exists(local_params_path):
                    with open(local_params_path, 'r') as fp:
                        params_json_str = fp.read()
            if not params_json_str:
                raise LookupError('parameters.settings.json file not found')
            try:
                self.parameters = nf_core.workflow.parameters.Parameters.create_from_json(params_json_str)
                for p in self.parameters:
                    self.parameter_keys.append(p.name)
                    logging.debug("Found param from parameters.settings.json: param.{}".format(p.name))
            except ValueError as e:
                logging.error("Could not parse pipeline parameters.settings.json JSON:\n  {}\n".format(e))
            except jsonschema.exceptions.ValidationError as e:
                logging.error("Validation error with pipeline parameters.settings.json:\n  Message: {}\n  Instance: {}\n".format(e.message, e.instance))
        except LookupError as e:
            print("WARNING: Could not parse parameter settings file for `{pipeline}`:\n  {exception}".format(
                pipeline=self.workflow, exception=e))

    def collect_pipeline_param_defaults(self):
        """ Collect the default params and values from the workflow """
        logging.debug("Collecting pipeline parameter defaults\n")
        config = nf_core.utils.fetch_wf_config(self.workflow, self.local_wf)
        for key, value in config.items():
            keys = key.split('.')
            if keys[0] == 'params' and len(keys) == 2 and keys[1] not in self.parameter_keys:

                # Try to guess the variable type from the default value
                p_type = 'string'
                p_default = str(value)
                # All digits - int
                if value.isdigit():
                    p_type = 'integer'
                    p_default = int(value)
                else:
                    # Not just digis - try converting to a float
                    try:
                        p_default = float(value)
                        p_type = 'decimal'
                    except ValueError:
                        pass
                # Strings 'true' and 'false' - booleans
                if value == 'true' or value == 'false':
                    p_type = 'boolean'
                    p_default = True if value == 'true' else False

                # Build the Parameter object
                parameter = (nf_core.workflow.parameters.Parameter.builder()
                             .name(keys[1])
                             .label(keys[1])
                             .usage(None)
                             .param_type(p_type)
                             .choices(None)
                             .default(p_default)
                             .pattern(".*")
                             .render("textfield")
                             .arity(None)
                             .group("Other pipeline parameters")
                             .build())
                self.parameters.append(parameter)
                self.parameter_keys.append(keys[1])
                logging.debug("Discovered param from `nextflow config`: param.{}".format(keys[1]))

        # Not all parameters can be found with `nextflow config` - try searching main.nf and config files
        searchfiles = []
        pattern = re.compile(r'params\.([\w\d]+)')
        wf_base = self.workflow if self.wf_ispath else self.local_wf.local_path
        if os.path.exists(os.path.join(wf_base, 'main.nf')):
            searchfiles.append(os.path.join(wf_base, 'main.nf'))
        if os.path.exists(os.path.join(wf_base, 'nextflow.config')):
            searchfiles.append(os.path.join(wf_base, 'nextflow.config'))
        if os.path.isdir(os.path.join(wf_base, 'conf')):
            for fn in os.listdir(os.path.join(wf_base, 'conf')):
                searchfiles.append(os.path.join(wf_base, 'conf', fn))
        for sf in searchfiles:
            with open(sf, 'r') as fh:
                for l in fh:
                    match = re.search(pattern, l)
                    if match:
                        param = match.group(1)
                        if param not in self.parameter_keys:
                            # Build the Parameter object
                            parameter = (nf_core.workflow.parameters.Parameter.builder()
                                         .name(param)
                                         .label(param)
                                         .usage(None)
                                         .param_type("string")
                                         .choices(None)
                                         .default("")
                                         .pattern(".*")
                                         .render("textfield")
                                         .arity(None)
                                         .group("Other pipeline parameters")
                                         .build())
                            self.parameters.append(parameter)
                            self.parameter_keys.append(param)
                            logging.debug("Discovered param from {}: param.{}".format(os.path.relpath(sf, wf_base), param))

    def prompt_core_nxf_flags(self):
        """ Ask the user if they want to override any default values """
        # Main nextflow flags
        click.secho("Main nextflow options", bold=True, underline=True)
        for flag, f_default in self.nxf_flag_defaults.items():

            # Click prompts don't like None, so we have to use an empty string instead
            f_default_print = f_default
            if f_default is None:
                f_default = ''
                f_default_print = 'None'

            # Overwrite the default prompt for boolean
            if isinstance(f_default, bool):
                f_default_print = 'Y/n' if f_default else 'y/N'

            # Prompt for a response
            f_user = click.prompt(
                "\n{}\n {} {}".format(
                    self.nxf_flag_help[flag],
                    click.style(flag, fg='blue'),
                    click.style('[{}]'.format(str(f_default_print)), fg='green')
                ),
                default = f_default,
                show_default = False
            )

            # Only save if we've changed the default
            if f_user != f_default:
                # Convert string bools to real bools
                try:
                    f_user = f_user.strip('"').strip("'")
                    if f_user.lower() == 'true': f_user = True
                    if f_user.lower() == 'false': f_user = False
                except AttributeError:
                    pass
                self.nxf_flags[flag] = f_user

    def group_parameters(self):
        """Groups parameters by their 'group' property.

        Args:
            parameters (list): Collection of parameter objects.

        Returns:
            dict: Parameter objects grouped by the `group` property.
        """
        for param in self.parameters:
            if param.group not in self.grouped_parameters.keys():
                self.grouped_parameters[param.group] = []
            self.grouped_parameters[param.group].append(param)

    def prompt_param_flags(self):
        """ Prompts the user for parameter input values and validates them. """
        for group_label, params in self.grouped_parameters.items():
            click.echo("\n\n{}{}".format(
                click.style('Parameter group: ', bold=True, underline=True),
                click.style(group_label, bold=True, underline=True, fg='red')
            ))
            use_defaults = click.confirm(
                "Do you want to change the group's defaults? "+click.style('[y/N]', fg='green'),
                    default=False, show_default=False)
            if not use_defaults:
                continue
            for parameter in params:
                # Skip this option if the render mode is none
                value_is_valid = parameter.render == 'none'
                first_attempt = True
                while not value_is_valid:
                    # Start building the string to show to the user - label and usage
                    plines = ['']
                    if parameter.label:
                        plines.append(click.style(parameter.label, bold=True))
                    if parameter.usage:
                        plines.append(click.style(parameter.usage))

                    # Add the choices / range if applicable
                    if parameter.choices:
                        rc = 'Choices' if parameter.type == 'string' else 'Range'
                        choices_string = ", ".join([click.style(x, fg='yellow') for x in parameter.choices if x != ''])
                        plines.append('{}: {}'.format(rc, choices_string))

                    # Reset the choice display if boolean
                    if parameter.type == "boolean":
                        pdef_val = 'Y/n' if parameter.default_value else 'y/N'
                    else:
                        pdef_val = parameter.default_value

                    # Final line to print - command and default
                    if pdef_val == '':
                        flag_default = ''
                    else:
                        flag_default = click.style(' [{}]'.format(pdef_val), fg='green')
                    flag_prompt = click.style(' --{}'.format(parameter.name), fg='blue') + flag_default


                    # Only show this final prompt if we're trying again
                    if first_attempt:
                        plines.append(flag_prompt)
                    else:
                        plines = [flag_prompt]
                    first_attempt = False

                    # Use click.confirm if a boolean for default input handling
                    if parameter.type == "boolean":
                        parameter.value = click.confirm("\n".join(plines),
                            default=parameter.default_value, show_default=False)
                    # Use click.prompt if anything else
                    else:
                        parameter.value = click.prompt("\n".join(plines),
                            default=parameter.default_value, show_default=False)

                    # Set input parameter types
                    try:
                        if parameter.type == "integer":
                            parameter.value = int(parameter.value)
                        elif parameter.type == "decimal":
                            parameter.value = float(parameter.value)
                        elif parameter.type == "string":
                            parameter.value = str(parameter.value)
                    except ValueError as e:
                        logging.error("Could not set variable type: {}".format(e))

                    # Validate the input
                    try:
                        parameter.validate()
                    except Exception as e:
                        click.secho("\nERROR: {}".format(e), fg='red')
                        click.secho("Please try again:")
                        continue
                    else:
                        value_is_valid = True

    def build_command(self):
        """ Build the nextflow run command based on what we know """
        for flag, val in self.nxf_flags.items():
            # Boolean flags like -resume
            if isinstance(val, bool):
                if val:
                    self.nextflow_cmd = "{} {}".format(self.nextflow_cmd, flag)
                else:
                    logging.warning("TODO: Can't set false boolean flags currently.")
            # String values
            else:
                self.nextflow_cmd = '{} {} "{}"'.format(self.nextflow_cmd, flag, val.replace('"', '\\"'))

        # Write the user selection to a file and run nextflow with that
        if self.use_params_file:
            path = self.create_nfx_params_file()
            if path is not None:
                self.nextflow_cmd = '{} {} "{}"'.format(self.nextflow_cmd, "--params-file", path)
            self.write_params_as_full_json()

        # Call nextflow with a list of command line flags
        else:
            for param, val in self.params_user.items():
                # Boolean flags like --saveTrimmed
                if isinstance(val, bool):
                    if val:
                        self.nextflow_cmd = "{} --{}".format(self.nextflow_cmd, param)
                    else:
                        logging.error("Can't set false boolean flags.")
                # everything else
                else:
                    self.nextflow_cmd = '{} --{} "{}"'.format(self.nextflow_cmd, param, val.replace('"', '\\"'))

    def create_nfx_params_file(self):
        working_dir = os.getcwd()
        output_file = os.path.join(working_dir, "nfx-params.json")
        json_string = nf_core.workflow.parameters.Parameters.in_nextflow_json(self.parameters, indent=4)
        if json_string == '{}':
            return None
        with open(output_file, "w") as fp:
            fp.write(json_string)
        return output_file

    def write_params_as_full_json(self, outdir = os.getcwd()):
        output_file = os.path.join(outdir, "full-params.json")
        json_string = nf_core.workflow.parameters.Parameters.in_full_json(self.parameters, indent=4)
        with open(output_file, "w") as fp:
            fp.write(json_string)
        return output_file

    def launch_workflow(self):
        """ Launch nextflow if required  """
        click.secho("\n\nNextflow command:", bold=True, underline=True)
        click.secho("  {}\n\n".format(self.nextflow_cmd), fg='magenta')

        if click.confirm(
            'Do you want to run this command now? '+click.style('[y/N]', fg='green'),
            default=False,
            show_default=False
            ):
            logging.info("Launching workflow!")
            subprocess.call(self.nextflow_cmd, shell=True)
