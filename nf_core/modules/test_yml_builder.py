#!/usr/bin/env python
"""
The ModulesTestYmlBuilder class handles automatic generation of the modules test.yml file
along with running the tests and creating md5 sums
"""

from __future__ import print_function
from rich.syntax import Syntax

import errno
import hashlib
import logging
import os
import questionary
import re
import rich
import shlex
import subprocess
import tempfile
import yaml
import operator

import nf_core.utils

from .modules_repo import ModulesRepo


log = logging.getLogger(__name__)


class ModulesTestYmlBuilder(object):
    def __init__(
        self,
        module_name=None,
        run_tests=False,
        test_yml_output_path=None,
        force_overwrite=False,
        no_prompts=False,
    ):
        self.module_name = module_name
        self.run_tests = run_tests
        self.test_yml_output_path = test_yml_output_path
        self.force_overwrite = force_overwrite
        self.no_prompts = no_prompts
        self.module_dir = None
        self.module_test_main = None
        self.entry_points = []
        self.tests = []

    def run(self):
        """Run build steps"""
        if not self.no_prompts:
            log.info(
                "[yellow]Press enter to use default values [cyan bold](shown in brackets) [yellow]or type your own responses"
            )
        self.check_inputs()
        self.scrape_workflow_entry_points()
        self.build_all_tests()
        self.print_test_yml()

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

        # Check that we're running tests if no prompts
        if not self.run_tests and self.no_prompts:
            log.debug("Setting run_tests to True as running without prompts")
            self.run_tests = True

        # Get the output YAML file / check it does not already exist
        while self.test_yml_output_path is None:
            default_val = f"tests/modules/{self.module_name}/test.yml"
            if self.no_prompts:
                self.test_yml_output_path = default_val
            else:
                self.test_yml_output_path = rich.prompt.Prompt.ask(
                    "[violet]Test YAML output path[/] (- for stdout)", default=default_val
                ).strip()
                if self.test_yml_output_path == "":
                    self.test_yml_output_path = None
                # Check that the output YAML file does not already exist
                if (
                    self.test_yml_output_path is not None
                    and self.test_yml_output_path != "-"
                    and os.path.exists(self.test_yml_output_path)
                    and not self.force_overwrite
                ):
                    if rich.prompt.Confirm.ask(
                        f"[red]File exists! [green]'{self.test_yml_output_path}' [violet]Overwrite?"
                    ):
                        self.force_overwrite = True
                    else:
                        self.test_yml_output_path = None
        if os.path.exists(self.test_yml_output_path) and not self.force_overwrite:
            raise UserWarning(
                f"Test YAML file already exists! '{self.test_yml_output_path}'. Use '--force' to overwrite."
            )

    def scrape_workflow_entry_points(self):
        """Find the test workflow entry points from main.nf"""
        log.info(f"Looking for test workflow entry points: '{self.module_test_main}'")
        with open(self.module_test_main, "r") as fh:
            for line in fh:
                match = re.match(r"workflow\s+(\S+)\s+{", line)
                if match:
                    self.entry_points.append(match.group(1))
        if len(self.entry_points) == 0:
            raise UserWarning("No workflow entry points found in 'self.module_test_main'")

    def build_all_tests(self):
        """
        Go over each entry point and build structure
        """
        for entry_point in self.entry_points:
            ep_test = self.build_single_test(entry_point)
            if ep_test:
                self.tests.append(ep_test)

    def build_single_test(self, entry_point):
        """Given the supplied cli flags, prompt for any that are missing.

        Returns: Test command
        """
        ep_test = {
            "name": "",
            "command": "",
            "tags": [],
            "files": [],
        }

        # Print nice divider line
        console = rich.console.Console()
        console.print("[black]" + "─" * console.width)

        log.info(f"Building test meta for entry point '{entry_point}'")

        while ep_test["name"] == "":
            default_val = f"{self.module_name.replace('/', ' ')} {entry_point}"
            if self.no_prompts:
                ep_test["name"] = default_val
            else:
                ep_test["name"] = rich.prompt.Prompt.ask("[violet]Test name", default=default_val).strip()

        while ep_test["command"] == "":
            default_val = (
                f"nextflow run tests/modules/{self.module_name} -entry {entry_point} -c tests/config/nextflow.config"
            )
            if self.no_prompts:
                ep_test["command"] = default_val
            else:
                ep_test["command"] = rich.prompt.Prompt.ask("[violet]Test command", default=default_val).strip()

        while len(ep_test["tags"]) == 0:
            mod_name_parts = self.module_name.split("/")
            tag_defaults = []
            for idx in range(0, len(mod_name_parts)):
                tag_defaults.append("/".join(mod_name_parts[: idx + 1]))
            # Remove duplicates
            tag_defaults = list(set(tag_defaults))
            if self.no_prompts:
                ep_test["tags"] = tag_defaults
            else:
                while len(ep_test["tags"]) == 0:
                    prompt_tags = rich.prompt.Prompt.ask(
                        "[violet]Test tags[/] (comma separated)", default=",".join(tag_defaults)
                    ).strip()
                    ep_test["tags"] = [t.strip() for t in prompt_tags.split(",")]

        ep_test["files"] = self.get_md5_sums(entry_point, ep_test["command"])

        return ep_test

    def _md5(self, fname):
        """Generate md5 sum for file"""
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        md5sum = hash_md5.hexdigest()
        return md5sum

    def create_test_file_dict(self, results_dir):
        """Walk through directory and collect md5 sums"""
        test_files = []
        for root, dir, file in os.walk(results_dir):
            for elem in file:
                elem = os.path.join(root, elem)
                elem_md5 = self._md5(elem)
                # Switch out the results directory path with the expected 'output' directory
                elem = elem.replace(results_dir, "output")
                test_files.append({"path": elem, "md5sum": elem_md5})

        test_files = sorted(test_files, key=operator.itemgetter("path"))

        return test_files

    def get_md5_sums(self, entry_point, command, results_dir=None, results_dir_repeat=None):
        """
        Recursively go through directories and subdirectories
        and generate tuples of (<file_path>, <md5sum>)
        returns: list of tuples
        """

        run_this_test = False
        while results_dir is None:
            if self.run_tests or run_this_test:
                results_dir, results_dir_repeat = self.run_tests_workflow(command)
            else:
                results_dir = rich.prompt.Prompt.ask(
                    f"[violet]Test output folder with results[/] (leave blank to run test)"
                )
                if results_dir == "":
                    results_dir = None
                    run_this_test = True
                elif not os.path.isdir(results_dir):
                    log.error(f"Directory '{results_dir}' does not exist")
                    results_dir = None

        test_files = self.create_test_file_dict(results_dir=results_dir)

        # If test was repeated, compare the md5 sums
        if results_dir_repeat:
            test_files_repeat = self.create_test_file_dict(results_dir=results_dir_repeat)

            # Compare both test.yml files
            for i in range(len(test_files)):
                if not test_files[i]["md5sum"] == test_files_repeat[i]["md5sum"]:
                    test_files[i].pop("md5sum")
                    test_files[i][
                        "contains"
                    ] = "[ # TODO nf-core: file md5sum was variable, please replace this text with a string found in the file instead ]"

        if len(test_files) == 0:
            raise UserWarning(f"Could not find any test result files in '{results_dir}'")

        return test_files

    def run_tests_workflow(self, command):
        """Given a test workflow and an entry point, run the test workflow"""

        # The config expects $PROFILE and Nextflow fails if it's not set
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

        tmp_dir = tempfile.mkdtemp()
        tmp_dir_repeat = tempfile.mkdtemp()
        work_dir = tempfile.mkdtemp()
        command_repeat = command + f" --outdir {tmp_dir_repeat} -work-dir {work_dir}"
        command += f" --outdir {tmp_dir} -work-dir {work_dir}"

        log.info(f"Running '{self.module_name}' test with command:\n[violet]{command}")
        try:
            nfconfig_raw = subprocess.check_output(shlex.split(command))
            log.info(f"Repeating test ...")
            nfconfig_raw = subprocess.check_output(shlex.split(command_repeat))

        except OSError as e:
            if e.errno == errno.ENOENT and command.strip().startswith("nextflow "):
                raise AssertionError(
                    "It looks like Nextflow is not installed. It is required for most nf-core functions."
                )
        except subprocess.CalledProcessError as e:
            raise UserWarning(f"Error running test workflow (exit code {e.returncode})\n[red]{e.output.decode()}")
        except Exception as e:
            raise UserWarning(f"Error running test workflow: {e}")
        else:
            log.info("Test workflow finished!")
            log.debug(nfconfig_raw)

        return tmp_dir, tmp_dir_repeat

    def print_test_yml(self):
        """
        Generate the test yml file.
        """

        if self.test_yml_output_path == "-":
            console = rich.console.Console()
            yaml_str = yaml.dump(self.tests, Dumper=nf_core.utils.custom_yaml_dumper(), width=10000000)
            console.print("\n", Syntax(yaml_str, "yaml"), "\n")
            return

        try:
            log.info(f"Writing to '{self.test_yml_output_path}'")
            with open(self.test_yml_output_path, "w") as fh:
                yaml.dump(self.tests, fh, Dumper=nf_core.utils.custom_yaml_dumper(), width=10000000)
        except FileNotFoundError as e:
            raise UserWarning("Could not create test.yml file: '{}'".format(e))
