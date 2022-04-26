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

import nf_core.utils
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)

class ModulesTest(object):
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
        self.check_inputs()
        self.set_profile()
        self.run_pytests()

    def check_inputs(self):
        """Do more complex checks about supplied flags."""

        # Get the tool name if not specified
        if self.module_name is None:
            modules_repo = ModulesRepo()
            modules_repo.get_modules_file_tree()
            self.module_name = questionary.autocomplete(
                "Tool name:",
                choices=modules_repo.modules_avail_module_names,
                style=nf_core.utils.nfcore_question_style,
            ).ask()
        self.module_dir = os.path.join("modules", *self.module_name.split("/"))
        self.module_test_main = os.path.join("tests", "modules", *self.module_name.split("/"), "main.nf")

        # First, sanity check that the module directory exists
        if not os.path.isdir(self.module_dir):
            raise UserWarning(f"Cannot find directory '{self.module_dir}'. Should be TOOL/SUBTOOL or TOOL")
        if not os.path.exists(self.module_test_main):
            raise UserWarning(f"Cannot find module test workflow '{self.module_test_main}'")

    def set_profile(self):
        """Set $PROFILE env variable.
        The config expects $PROFILE and Nextflow fails if it's not set.
        """
        if os.environ.get("PROFILE") is None:
            os.environ["PROFILE"] = ""
            if self.no_prompts:
                log.info(
                    "Setting env var '$PROFILE' to an empty string as not set.\n"
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
                if profile in ["singularity", "conda"]:
                    os.environ["PROFILE"] = profile
                    log.info(f"Setting env var '$PROFILE' to '{profile}'")

    def run_pytests(self):
        """Given a module name, run tests."""
        # Print nice divider line
        console = rich.console.Console()
        console.print("[black]" + "─" * console.width)

        # Set pytest arguments
        command_args = ["--tag", f"{self.module_name}", "--symlink", "--keep-workflow-wd"]
        command_args += self.pytest_args

        # Run pytest
        log.info(f"Running pytest for module '{self.module_name}'")
        sys.exit(pytest.main(command_args))
