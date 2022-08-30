#!/usr/bin/env python
"""
The ModulesTest class runs the tests locally
"""

import logging
import os
import sys
from pathlib import Path
from shutil import which

import pytest
import questionary
import rich

import nf_core.modules.module_utils
import nf_core.utils
from nf_core.modules.modules_command import ModuleCommand
from nf_core.modules.modules_json import ModulesJson

log = logging.getLogger(__name__)


class ModulesTest(ModuleCommand):
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
        remote_url=None,
        branch=None,
        no_pull=False,
    ):
        self.module_name = module_name
        self.no_prompts = no_prompts
        self.pytest_args = pytest_args

        super().__init__(".", remote_url, branch, no_pull)

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

        # Retrieving installed modules
        if self.repo_type == "modules":
            installed_modules = self.get_modules_clone_modules()
        else:
            modules_json = ModulesJson(self.dir)
            modules_json.check_up_to_date()
            installed_modules = modules_json.get_all_modules().get(self.modules_repo.fullname)

        # Get the tool name if not specified
        if self.module_name is None:
            if self.no_prompts:
                raise UserWarning(
                    "Tool name not provided and prompts deactivated. Please provide the tool name as TOOL/SUBTOOL or TOOL."
                )
            if not installed_modules:
                raise UserWarning(
                    f"No installed modules were found from '{self.modules_repo.remote_url}'.\n"
                    f"Are you running the tests inside the nf-core/modules main directory?\n"
                    f"Otherwise, make sure that the directory structure is modules/TOOL/SUBTOOL/ and tests/modules/TOOLS/SUBTOOL/"
                )
            self.module_name = questionary.autocomplete(
                "Tool name:",
                choices=installed_modules,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Sanity check that the module directory exists
        self._validate_folder_structure()

    def _validate_folder_structure(self):
        """Validate that the modules follow the correct folder structure to run the tests:
        - modules/TOOL/SUBTOOL/
        - tests/modules/TOOL/SUBTOOL/

        """
        basedir = "modules/nf-core"

        if self.repo_type == "modules":
            module_path = Path("modules") / self.module_name
            test_path = Path("tests/modules") / self.module_name
        else:
            module_path = Path(f"{basedir}/modules") / self.module_name
            test_path = Path(f"{basedir}/tests/modules") / self.module_name

        if not (self.dir / module_path).is_dir():
            raise UserWarning(
                f"Cannot find directory '{module_path}'. Should be TOOL/SUBTOOL or TOOL. Are you running the tests inside the nf-core/modules main directory?"
            )
        if not (self.dir / test_path).is_dir():
            raise UserWarning(
                f"Cannot find directory '{test_path}'. Should be TOOL/SUBTOOL or TOOL. "
                "Are you running the tests inside the nf-core/modules main directory? "
                "Do you have tests for the specified module?"
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
