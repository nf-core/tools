#!/usr/bin/env python
""" Launch a pipeline, interactively collecting params """

from __future__ import print_function

import click
import logging
import os
import subprocess

import nf_core.utils, nf_core.list
import nf_core.workflow.parameters, nf_core.workflow.validation, nf_core.workflow.workflow

def launch_pipeline(workflow, params_local_uri, direct):
    launcher = Launch(workflow)
    params_list = []

    # Get nextflow to fetch the workflow if we don't already have it
    if not launcher.local_wf:
        logging.info("Downloading workflow: {}".format(launcher.workflow))
        try:
            with open(os.devnull, 'w') as devnull:
                nfconfig_raw = subprocess.check_output(['nextflow', 'pull', launcher.workflow], stderr=devnull)
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
        except subprocess.CalledProcessError as e:
            raise AssertionError("`nextflow pull` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
        else:
            launcher.local_wf = nf_core.list.LocalWorkflow(launcher.workflow)

    # Get the pipeline default parameters
    try:
        params_json_str = None
        # Params file supplied to launch command
        if params_local_uri:
            with open(params_local_uri, 'r') as fp:
                params_json_str = fp.read()
        # Get workflow file from local cached copy
        else:
            local_params_path = os.path.join(launcher.local_wf.local_path, 'parameters.settings.json')
            if os.path.exists(local_params_path):
                with open(params_local_uri, 'r') as fp:
                    params_json_str = fp.read()
        if not params_json_str:
            raise LookupError
        params_list = nf_core.workflow.parameters.Parameters.create_from_json(params_json_str)
    except LookupError as e:
        print("WARNING: No parameter settings file found for `{pipeline}`.\n{exception}".format(
            pipeline=launcher.workflow, exception=e))

    # Fallback if parameters.settings.json not found, calls Nextflow's config command
    if not params_list:
        launcher.collect_defaults()

    # Kick off the interactive wizard to collect user inputs
    launcher.prompt_vars(params_list, direct)

    # Build and launch the `nextflow run` command
    launcher.build_command(params_list)
    launcher.launch_workflow()

class Launch(object):
    """ Class to hold config option to launch a pipeline """

    def __init__(self, workflow):
        """ Initialise the class with empty placeholder vars """

        # Prepend nf-core/ if it seems sensible
        if 'nf-core' not in workflow and workflow.count('/') == 0 and not os.path.exists(workflow):
            workflow = "nf-core/{}".format(workflow)
            logging.debug("Prepending nf-core/ to workflow")
        logging.info("Launching {}\n".format(workflow))

        # Get local workflows to see if we have a cached version
        self.local_wf = None
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
        self.param_defaults = {}
        self.params = {}
        self.nextflow_cmd = "nextflow run {}".format(self.workflow)

    def collect_defaults(self):
        """ Collect the default params and values from the workflow """
        config = nf_core.utils.fetch_wf_config(self.workflow)
        for key, value in config.items():
            keys = key.split('.')
            if keys[0] == 'params' and len(keys) == 2:
                self.param_defaults[keys[1]] = value

    def prompt_vars(self, params = None, direct = False):
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

        # Uses the parameter values from the JSON file
        # and does not ask the user to set them explicitly
        if direct:
            return

        # Pipeline params
        if params:
            Launch.__prompt_defaults_from_param_objects(
                Launch.__group_parameters(params)
                )
            return
        for param, p_default in self.param_defaults.items():
            if not isinstance(p_default, dict) and not isinstance(p_default, list):

                # Prompt for a response
                p_user = click.prompt(
                    "\n --{} {}".format(
                        click.style(param, fg='blue'),
                        click.style('[{}]'.format(str(p_default)), fg='green')
                    ),
                    default = p_default,
                    show_default = False
                )

                # Only save if we've changed the default
                if p_user != p_default:
                    # Convert string bools to real bools
                    try:
                        p_user = p_user.strip('"').strip("'")
                        if p_user.lower() == 'true': p_user = True
                        if p_user.lower() == 'false': p_user = False
                    except AttributeError:
                        pass
                    self.params[param] = p_user

    @classmethod
    def __group_parameters(cls, parameters):
        """Groups parameters by their 'group' property.

        Args:
            parameters (list): Collection of parameter objects.

        Returns:
            dict: Parameter objects grouped by the `group` property.
        """
        grouped_parameters = {}
        for param in parameters:
            if not grouped_parameters.get(param.group):
                grouped_parameters[param.group] = []
            grouped_parameters[param.group].append(param)
        return grouped_parameters

    @classmethod
    def __prompt_defaults_from_param_objects(cls, params_grouped):
        """Prompts the user for parameter input values and validates them.

        Args:
            params_grouped (dict): A dictionary with parameter group labels
                as keys and list of parameters as values. ::

                {
                    "group1": [param1, param2],
                    ...
                }
        """
        for group_label, params in params_grouped.items():
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
                value_is_valid = False
                first_attempt = True
                while not value_is_valid:
                    # Start building the string to show to the user - label and usage
                    plines = ['',
                        click.style(parameter.label, bold=True),
                        click.style(parameter.usage, dim=True)
                    ]
                    # Add the choices / range if applicable
                    if parameter.choices:
                        rc = 'Choices' if parameter.type == 'string' else 'Range'
                        plines.append('{}: {}'.format(rc, str(parameter.choices)))

                    # Reset the choice display if boolean
                    if parameter.type == "boolean":
                        pdef_val = 'Y/n' if parameter.default_value else 'y/N'
                    else:
                        pdef_val = parameter.default_value

                    # Final line to print - command and default
                    flag_prompt = click.style(' --{} '.format(parameter.name), fg='blue') + \
                        click.style('[{}]'.format(pdef_val), fg='green')
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
                    if parameter.type == "integer":
                        parameter.value = int(parameter.value)
                    elif parameter.type == "decimal":
                        parameter.value = float(parameter.value)

                    # Validate the input
                    try:
                        parameter.validate()
                    except Exception as e:
                        click.secho("\nERROR: {}".format(e), fg='red')
                        click.secho("Please try again:")
                        continue
                    else:
                        value_is_valid = True

    def build_command(self, params = None):
        """ Build the nextflow run command based on what we know """
        for flag, val in self.nxf_flags.items():
            # Boolean flags like -resume
            if isinstance(val, bool):
                if val:
                    self.nextflow_cmd = "{} {}".format(self.nextflow_cmd, flag)
                else:
                    logging.warn("TODO: Can't set false boolean flags currently.")
            # String values
            else:
                self.nextflow_cmd = '{} {} "{}"'.format(self.nextflow_cmd, flag, val.replace('"', '\\"'))

        if params:  # When a parameter specification file was used, we can run Nextflow with it
            path = Launch.__create_nfx_params_file(params)
            self.nextflow_cmd = '{} {} "{}"'.format(self.nextflow_cmd, "--params-file", path)
            Launch.__write_params_as_full_json(params)
            return

        for param, val in self.params.items():
            # Boolean flags like --saveTrimmed
            if isinstance(val, bool):
                if val:
                    self.nextflow_cmd = "{} --{}".format(self.nextflow_cmd, param)
                else:
                    logging.warn("TODO: Can't set false boolean flags currently.")
            # everything else
            else:
                self.nextflow_cmd = '{} --{} "{}"'.format(self.nextflow_cmd, param, val.replace('"', '\\"'))

    @classmethod
    def __create_nfx_params_file(cls, params):
        working_dir = os.getcwd()
        output_file = os.path.join(working_dir, "nfx-params.json")
        json_string = nf_core.workflow.parameters.Parameters.in_nextflow_json(params, indent=4)
        with open(output_file, "w") as fp:
            fp.write(json_string)
        return output_file

    @classmethod
    def __write_params_as_full_json(cls, params, outdir = os.getcwd()):
        output_file = os.path.join(outdir, "full-params.json")
        json_string = nf_core.workflow.parameters.Parameters.in_full_json(params, indent=4)
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
