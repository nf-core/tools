#!/usr/bin/env python
"""
The ModulesTest class runs the tests locally
"""

import logging
import questionary
import os
import pytest
import sys
import rich
from pathlib import Path
from shutil import which

import nf_core.utils
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModulesTest(object):
    """
    Class to run module pytests.

    ...

    Attributes
    ----------
    module_name : str
        name of the tool to run tests for
    no_prompts : bool
        flat indicating if prompts are used
    pytest_args : tuple
        additional arguments passed to pytest command

    Methods
    -------
    run():
        Run test steps
    _check_inputs():
        Check inputs. Ask for module_name if not provided and check that the directory exists
    _set_profile():
        Set software profile
    _run_pytests(self):
        Run pytest
    """

    def __init__(
        self,
        module_name=None,
        no_prompts=False,
        pytest_args="",
    ):
        self.module_name = module_name
        self.no_prompts = no_prompts
        self.pytest_args = pytest_args

    def run(self):
        """Run test steps"""
        if not self.no_prompts:
            log.info(
                "[yellow]Press enter to use default values [cyan bold](shown in brackets) [yellow]or type your own responses"
            )
        self._check_inputs()
        self._set_profile()
        self._check_profile()
        self._run_pytests()

    def _check_inputs(self):
        """Do more complex checks about supplied flags."""

        # Get the tool name if not specified
        if self.module_name is None:
            if self.no_prompts:
                raise UserWarning(
                    "Tool name not provided and prompts deactivated. Please provide the tool name as TOOL/SUBTOOL or TOOL."
                )
            modules_repo = ModulesRepo()
            modules_repo.get_modules_file_tree()
            self.module_name = questionary.autocomplete(
                "Tool name:",
                choices=modules_repo.modules_avail_module_names,
                style=nf_core.utils.nfcore_question_style,
            ).ask()
        module_dir = Path("modules") / self.module_name

        # First, sanity check that the module directory exists
        if not module_dir.is_dir():
            raise UserWarning(
                f"Cannot find directory '{module_dir}'. Should be TOOL/SUBTOOL or TOOL. Are you running the tests inside the nf-core/modules main directory?"
            )

    def _set_profile(self):
        """Set $PROFILE env variable.
        The config expects $PROFILE and Nextflow fails if it's not set.
        """
        if os.environ.get("PROFILE") is None:
            os.environ["PROFILE"] = ""
            if self.no_prompts:
                log.info(
                    "Setting environment variable '$PROFILE' to an empty string as not set.\n"
                    "Tests will run with Docker by default. "
                    "To use Singularity set 'export PROFILE=singularity' in your shell before running this command."
                )
            else:
                question = {
                    "type": "list",
                    "name": "profile",
                    "message": "Choose software profile",
                    "choices": ["Docker", "Singularity", "Conda"],
                }
                answer = questionary.unsafe_prompt([question], style=nf_core.utils.nfcore_question_style)
                profile = answer["profile"].lower()
                os.environ["PROFILE"] = profile
                log.info(f"Setting environment variable '$PROFILE' to '{profile}'")

    def _check_profile(self):
        """Check if profile is available"""
        profile = os.environ.get("PROFILE")
        # Make sure the profile read from the environment is a valid Nextflow profile.
        valid_nextflow_profiles = ["docker", "singularity", "conda"]
        if profile in valid_nextflow_profiles:
            if not which(profile):
                raise UserWarning(f"Command '{profile}' not found - is it installed?")
        else:
            raise UserWarning(
                f"The PROFILE '{profile}' set in the shell environment is not valid.\n"
                f"Valid Nextflow profiles are '{', '.join(valid_nextflow_profiles)}'."
            )

    def _run_pytests(self):
        """Given a module name, run tests."""
        # Print nice divider line
        console = rich.console.Console()
        console.rule(self.module_name, style="black")

        # Set pytest arguments
        command_args = ["--tag", f"{self.module_name}", "--symlink", "--keep-workflow-wd", "--git-aware"]
        command_args += self.pytest_args

        # Run pytest
        log.info(f"Running pytest for module '{self.module_name}'")
        sys.exit(pytest.main(command_args))
