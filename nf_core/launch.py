#!/usr/bin/env python
""" Launch a pipeline, interactively collecting params """

from __future__ import print_function

import click
import logging
import os
import subprocess

import nf_core.utils
from nf_core.workflow import parameters as pms

def launch_pipeline(workflow, params_local_uri, direct):
    launcher = Launch(workflow)
    params_list = []
    try:
        if params_local_uri:
            with open(params_local_uri, 'r') as fp: params_json_str = fp.read() 
        else:
            params_json_str = nf_core.utils.fetch_parameter_settings_from_github(workflow)
        params_list = pms.Parameters.create_from_json(params_json_str)
    except LookupError as e:
        print("WARNING: No parameter settings file found for `{pipeline}`.\n{exception}".format(
            pipeline=workflow, exception=e))
    if not params_list:
        launcher.collect_defaults()  # Fallback, calls Nextflow's config command
    launcher.prompt_vars(params_list, direct)
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

        self.workflow = workflow
        self.nxf_flag_defaults = {
            '-name': False,
            '-r': False,
            '-profile': 'standard',
            '-w': os.getenv('NXF_WORK') if os.getenv('NXF_WORK') else 'work',
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
        logging.info("Main nextflow options:\n")
        for flag, f_default in self.nxf_flag_defaults.items():
            f_user = click.prompt(self.nxf_flag_help[flag], default=f_default)
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
        logging.info("Pipeline specific parameters:\n")
        if params:
            Launch.__prompt_defaults_from_param_objects(params)
            return
        for param, p_default in self.param_defaults.items():
            if not isinstance(p_default, dict) and not isinstance(p_default, list):
                p_user = click.prompt("--{}".format(param), default=p_default)
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
    def __prompt_defaults_from_param_objects(cls, params):
        for parameter in params:
            value_is_valid = False
            while(not value_is_valid):
                desired_param_value = click.prompt("'--{name}'\n"
                        "\tUsage: {usage}\n"
                        "\tRange/Choices: {choices}.\n"
                        .format(name=parameter.name,
                                usage=parameter.usage,
                                choices=parameter.choices),
                    default=parameter.default_value)
                if parameter.type == "integer":
                    desired_param_value = int(desired_param_value)
                elif parameter.type == "boolean":
                    desired_param_value = (str(desired_param_value).lower() in ['yes', 'y', 'true', 't', '1'])
                elif parameter.type == "decimal":
                    desired_param_value = float(desired_param_value)
                parameter.value = desired_param_value
                try:
                    parameter.validate()
                except Exception as e:
                    print(e)
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
        json_string = pms.Parameters.in_nextflow_json(params, indent=4)
        with open(output_file, "w") as fp:
            fp.write(json_string)
        return output_file
    
    @classmethod
    def __write_params_as_full_json(cls, params, outdir = os.getcwd()):
        output_file = os.path.join(outdir, "full-params.json")
        json_string = pms.Parameters.in_full_json(params, indent=4)
        with open(output_file, "w") as fp:
            fp.write(json_string)
        return output_file

    def launch_workflow(self):
        """ Launch nextflow if required  """
        logging.info("Nextflow command:\n  {}\n\n".format(self.nextflow_cmd))
        if click.confirm('Do you want to run this command now?'):
            logging.info("Launching!")
            subprocess.call(self.nextflow_cmd, shell=True)
