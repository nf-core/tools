import logging
import os
import sys
from pathlib import Path
from shutil import which

import pytest
import questionary
import rich
from git import InvalidGitRepositoryError, Repo

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.components_command import ComponentCommand
from nf_core.modules.modules_json import ModulesJson

log = logging.getLogger(__name__)


class ComponentsTest(ComponentCommand):
    """
    Class to run module and subworkflow pytests.

    ...

    Attributes
    ----------
    component_name : str
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
        Check inputs. Ask for component_name if not provided and check that the directory exists
    _set_profile():
        Set software profile
    _run_pytests(self):
        Run pytest
    """

    def __init__(
        self,
        component_type,
        component_name=None,
        no_prompts=False,
        pytest_args="",
        remote_url=None,
        branch=None,
        no_pull=False,
    ):
        super().__init__(component_type=component_type, dir=".", remote_url=remote_url, branch=branch, no_pull=no_pull)
        self.component_name = component_name
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
        # Check modules directory structure
        self.check_modules_structure()

        # Retrieving installed modules
        if self.repo_type == "modules":
            installed_components = self.get_components_clone_modules()
        else:
            modules_json = ModulesJson(self.dir)
            modules_json.check_up_to_date()
            installed_components = modules_json.get_all_components(self.component_type).get(
                self.modules_repo.remote_url
            )

        # Get the component name if not specified
        if self.component_name is None:
            if self.no_prompts:
                raise UserWarning(
                    f"{self.component_type[:-1].title()} name not provided and prompts deactivated. Please provide the {self.component_type[:-1]} name{' as TOOL/SUBTOOL or TOOL' if self.component_type == 'modules' else ''}."
                )
            if not installed_components:
                if self.component_type == "modules":
                    dir_structure_message = f"modules/{self.modules_repo.repo_path}/TOOL/SUBTOOL/ and tests/modules/{self.modules_repo.repo_path}/TOOLS/SUBTOOL/"
                elif self.component_type == "subworkflows":
                    dir_structure_message = f"subworkflows/{self.modules_repo.repo_path}/SUBWORKFLOW/ and tests/subworkflows/{self.modules_repo.repo_path}/SUBWORKFLOW/"
                raise UserWarning(
                    f"No installed {self.component_type} were found from '{self.modules_repo.remote_url}'.\n"
                    f"Are you running the tests inside the repository root directory?\n"
                    f"Make sure that the directory structure is {dir_structure_message}"
                )
            self.component_name = questionary.autocomplete(
                f"{self.component_type[:-1]} name:",
                choices=installed_components,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Sanity check that the module directory exists
        self._validate_folder_structure()

    def _validate_folder_structure(self):
        """Validate that the modules follow the correct folder structure to run the tests:
        - modules/nf-core/TOOL/SUBTOOL/
        - tests/modules/nf-core/TOOL/SUBTOOL/
        or
        - subworkflows/nf-core/SUBWORKFLOW/
        - tests/subworkflows/nf-core/SUBWORKFLOW/
        """
        if self.component_type == "modules":
            component_path = Path(self.default_modules_path) / self.component_name
            test_path = Path(self.default_tests_path) / self.component_name
        elif self.component_type == "subworkflows":
            component_path = Path(self.default_subworkflows_path) / self.component_name
            test_path = Path(self.default_subworkflows_tests_path) / self.component_name

        if not (self.dir / component_path).is_dir():
            raise UserWarning(
                f"Cannot find directory '{component_path}'. Should be {'TOOL/SUBTOOL or TOOL' if self.component_type == 'modules' else 'SUBWORKFLOW'}. Are you running the tests inside the modules repository root directory?"
            )
        if not (self.dir / test_path).is_dir():
            raise UserWarning(
                f"Cannot find directory '{test_path}'. Should be {'TOOL/SUBTOOL or TOOL' if self.component_type == 'modules' else 'SUBWORKFLOW'}. "
                "Are you running the tests inside the modules repository root directory? "
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
        """Given a module/subworkflow name, run tests."""
        # Print nice divider line
        console = rich.console.Console()
        console.rule(self.component_name, style="black")

        # Check uncommitted changed
        try:
            repo = Repo(self.dir)
            if repo.is_dirty():
                log.warning("You have uncommitted changes. Make sure to commit last changes before running the tests.")
        except InvalidGitRepositoryError:
            pass

        # Set pytest arguments
        tag = self.component_name
        if self.component_type == "subworkflows":
            tag = "subworkflows/" + tag
        command_args = ["--tag", f"{tag}", "--symlink", "--keep-workflow-wd", "--git-aware"]
        command_args += self.pytest_args

        # Run pytest
        log.info(f"Running pytest for {self.component_type[:-1]} '{self.component_name}'")
        sys.exit(pytest.main(command_args))
