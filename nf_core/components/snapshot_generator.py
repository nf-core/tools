"""
The ComponentTestSnapshotGenerator class handles the generation nf-test snapshots.
"""

from __future__ import print_function

import logging
import os
import re
from pathlib import Path
from typing import List, Optional

import questionary
from rich import print
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.text import Text

import nf_core.utils
from nf_core.components.components_command import ComponentCommand

log = logging.getLogger(__name__)


class ComponentTestSnapshotGenerator(ComponentCommand):
    """
    Class to generate nf-test snapshots for modules.
    """

    def __init__(
        self,
        component_type: str,
        component_name: Optional[str] = None,
        directory: str = ".",
        run_tests: bool = False,
        no_prompts: bool = False,
        remote_url: Optional[str] = None,
        branch: Optional[str] = None,
        verbose: bool = False,
        update: bool = False,
    ):
        super().__init__(component_type, directory, remote_url, branch)
        self.component_name = component_name
        self.remote_url = remote_url
        self.branch = branch
        self.run_tests = run_tests
        self.no_prompts = no_prompts
        self.component_dir: str | Path = directory
        self.errors: List[str] = []
        self.verbose = verbose
        self.obsolete_snapshots: bool = False
        self.update = update

    def run(self) -> None:
        """Run build steps"""
        self.check_inputs()
        self.check_snapshot_stability()
        if len(self.errors) > 0:
            errors = "\n - ".join(self.errors)
            raise UserWarning(f"Ran, but found errors:\n - {errors}")
        else:
            log.info("All tests passed!")

    def check_inputs(self) -> None:
        """Do more complex checks about supplied flags."""
        # Check modules directory structure
        if self.component_type == "modules":
            self.check_modules_structure()

        # Get the component name if not specified
        if self.component_name is None:
            self.component_name = questionary.autocomplete(
                "Tool name:" if self.component_type == "modules" else "Subworkflow name:",
                choices=self.components_from_repo(self.org),
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
        if self.component_dir == "":
            self.component_dir = Path(self.component_type, self.modules_repo.repo_path, *self.component_name.split("/"))

        # First, sanity check that the module directory exists
        if not Path(self.dir, self.component_dir).is_dir():
            raise UserWarning(
                f"Cannot find directory '{self.component_dir}'.{' Should be TOOL/SUBTOOL or TOOL' if self.component_type == 'modules' else ''}"
            )

        # Check that we're running tests if no prompts
        if not self.run_tests and self.no_prompts:
            log.debug("Setting run_tests to True as running without prompts")
            self.run_tests = True

        # Check container software to use
        if os.environ.get("PROFILE") is None:
            os.environ["PROFILE"] = ""
            if self.no_prompts:
                log.info(
                    "Setting env var '$PROFILE' to Docker as not set.\n"
                    "To use Singularity set 'export PROFILE=singularity' in your shell before running this command."
                )
                os.environ["PROFILE"] = "docker"
            else:
                question = {
                    "type": "list",
                    "name": "profile",
                    "message": "Choose container software to run the test with",
                    "choices": ["Docker", "Singularity", "Conda"],
                }
                answer = questionary.unsafe_prompt([question], style=nf_core.utils.nfcore_question_style)
                profile = answer["profile"].lower()
                os.environ["PROFILE"] = profile

    def display_nftest_output(self, nftest_out: bytes, nftest_err: bytes) -> None:
        nftest_output = Text.from_ansi(nftest_out.decode())
        print(Panel(nftest_output, title="nf-test output"))
        if nftest_err:
            syntax = Syntax(nftest_err.decode(), "java", theme="ansi_dark")
            print(Panel(syntax, title="nf-test error"))

    def generate_snapshot(self) -> bool:
        """Generate the nf-test snapshot using `nf-test test` command

        returns True if the test was successful, False otherwise
        """

        log.debug("Running nf-test test")

        # set verbose flag if self.verbose is True
        verbose = "--verbose --debug" if self.verbose else ""
        update = "--update-snapshot" if self.update else ""
        self.update = False  # reset self.update to False to test if the new snapshot is stable

        result = nf_core.utils.run_cmd(
            "nf-test",
            f"test {self.dir} --tag {self.component_name} --profile {os.environ['PROFILE']} {verbose} {update}",
        )
        if result is not None:
            nftest_out, nftest_err = result
            self.display_nftest_output(nftest_out, nftest_err)
            # check if nftest_out contains obsolete snapshots
            pattern = r"Snapshot Summary:.*?(\d+)\s+obsolete"
            compiled_pattern = re.compile(pattern, re.DOTALL)  # re.DOTALL to allow . to match newlines
            obsolete_snapshots = compiled_pattern.search(nftest_out.decode())
            if obsolete_snapshots:
                self.obsolete_snapshots = True

            # check if nf-test was successful
            if "Assertion failed:" in nftest_out.decode():
                return False
            else:
                log.debug("nf-test successful")
                return True
        else:
            log.error("nf-test failed")
            return False

    def check_snapshot_stability(self) -> bool:
        """Run the nf-test twice and check if the snapshot changes"""
        log.info("Generating nf-test snapshot")
        if not self.generate_snapshot():
            log.error("nf-test failed")
            self.errors.append("nf-test failed")
            return False  # stop here if the first run failed
        log.info("Generating nf-test snapshot again to check stability")
        if not self.generate_snapshot():
            log.error("nf-test snapshot is not stable")
            self.errors.append("nf-test snapshot is not stable")
            return False
        else:
            if self.obsolete_snapshots:
                # ask if the user wants to remove obsolete snapshots using nf-test --clean-snapshot
                if self.no_prompts:
                    log.info("Removing obsolete snapshots")
                    nf_core.utils.run_cmd(
                        "nf-test",
                        f"test {self.dir} --tag {self.component_name} --profile {os.environ['PROFILE']} --clean-snapshot",
                    )
                else:
                    answer = Confirm.ask("nf-test found obsolete snapshots. Do you want to remove them?", default=True)
                    if answer:
                        log.info("Removing obsolete snapshots")
                        nf_core.utils.run_cmd(
                            "nf-test",
                            f"test {self.dir} --tag {self.component_name} --profile {os.environ['PROFILE']} --clean-snapshot",
                        )
                    else:
                        log.debug("Obsolete snapshots not removed")
            return True
