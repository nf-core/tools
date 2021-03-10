#!/usr/bin/env python
"""
Code to handle DSL2 module imports from a GitHub repository
"""

from __future__ import print_function
from rich.console import Console
from rich.syntax import Syntax

import base64
import errno
import hashlib
import logging
import os
import re
import requests
import rich
import shlex
import shutil
import subprocess
import sys
import tempfile
import yaml

log = logging.getLogger(__name__)


class ModulesRepo(object):
    """
    An object to store details about the repository being used for modules.

    Used by the `nf-core modules` top-level command with -r and -b flags,
    so that this can be used in the same way by all sucommands.
    """

    def __init__(self, repo="nf-core/modules", branch="master"):
        self.name = repo
        self.branch = branch


class PipelineModules(object):
    def __init__(self):
        """
        Initialise the PipelineModules object
        """
        self.modules_repo = ModulesRepo()
        self.pipeline_dir = None
        self.modules_file_tree = {}
        self.modules_current_hash = None
        self.modules_avail_module_names = []

    def list_modules(self):
        """
        Get available module names from GitHub tree for repo
        and print as list to stdout
        """
        self.get_modules_file_tree()
        return_str = ""

        if len(self.modules_avail_module_names) > 0:
            log.info("Modules available from {} ({}):\n".format(self.modules_repo.name, self.modules_repo.branch))
            # Print results to stdout
            return_str += "\n".join(self.modules_avail_module_names)
        else:
            log.info(
                "No available modules found in {} ({}):\n".format(self.modules_repo.name, self.modules_repo.branch)
            )
        return return_str

    def install(self, module):

        log.info("Installing {}".format(module))

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the available modules
        self.get_modules_file_tree()

        # Check that the supplied name is an available module
        if module not in self.modules_avail_module_names:
            log.error("Module '{}' not found in list of available modules.".format(module))
            log.info("Use the command 'nf-core modules list' to view available software")
            return False
        log.debug("Installing module '{}' at modules hash {}".format(module, self.modules_current_hash))

        # Check that we don't already have a folder for this module
        module_dir = os.path.join(self.pipeline_dir, "modules", "nf-core", "software", module)
        if os.path.exists(module_dir):
            log.error("Module directory already exists: {}".format(module_dir))
            log.info("To update an existing module, use the commands 'nf-core update' or 'nf-core fix'")
            return False

        # Download module files
        files = self.get_module_file_urls(module)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            dl_filename = os.path.join(self.pipeline_dir, "modules", "nf-core", filename)
            self.download_gh_file(dl_filename, api_url)
        log.info("Downloaded {} files to {}".format(len(files), module_dir))

    def update(self, module, force=False):
        log.error("This command is not yet implemented")
        pass

    def remove(self, module):
        """
        Remove an already installed module
        This command only works for modules that are installed from 'nf-core/modules'
        """
        log.info("Removing {}".format(module))

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the module directory
        module_dir = os.path.join(self.pipeline_dir, "modules", "nf-core", "software", module)

        # Verify that the module is actually installed
        if not os.path.exists(module_dir):
            log.error("Module directory does not installed: {}".format(module_dir))
            log.info("The module you want to remove seems not to be installed. Is it a local module?")
            return False

        # Remove the module
        try:
            shutil.rmtree(module_dir)
            log.info("Successfully removed {} module".format(module))
            return True
        except OSError as e:
            log.error("Could not remove module: {}".format(e))
            return False

    def check_modules(self):
        log.error("This command is not yet implemented")
        pass

    def get_modules_file_tree(self):
        """
        Fetch the file list from the repo, using the GitHub API

        Sets self.modules_file_tree
             self.modules_current_hash
             self.modules_avail_module_names
        """
        api_url = "https://api.github.com/repos/{}/git/trees/{}?recursive=1".format(
            self.modules_repo.name, self.modules_repo.branch
        )
        r = requests.get(api_url)
        if r.status_code == 404:
            log.error(
                "Repository / branch not found: {} ({})\n{}".format(
                    self.modules_repo.name, self.modules_repo.branch, api_url
                )
            )
            sys.exit(1)
        elif r.status_code != 200:
            raise SystemError(
                "Could not fetch {} ({}) tree: {}\n{}".format(
                    self.modules_repo.name, self.modules_repo.branch, r.status_code, api_url
                )
            )

        result = r.json()
        assert result["truncated"] == False

        self.modules_current_hash = result["sha"]
        self.modules_file_tree = result["tree"]
        for f in result["tree"]:
            if f["path"].startswith("software/") and f["path"].endswith("/main.nf") and "/test/" not in f["path"]:
                # remove software/ and /main.nf
                self.modules_avail_module_names.append(f["path"][9:-8])

    def get_module_file_urls(self, module):
        """Fetch list of URLs for a specific module

        Takes the name of a module and iterates over the GitHub repo file tree.
        Loops over items that are prefixed with the path 'software/<module_name>' and ignores
        anything that's not a blob. Also ignores the test/ subfolder.

        Returns a dictionary with keys as filenames and values as GitHub API URIs.
        These can be used to then download file contents.

        Args:
            module (string): Name of module for which to fetch a set of URLs

        Returns:
            dict: Set of files and associated URLs as follows:

            {
                'software/fastqc/main.nf': 'https://api.github.com/repos/nf-core/modules/git/blobs/65ba598119206a2b851b86a9b5880b5476e263c3',
                'software/fastqc/meta.yml': 'https://api.github.com/repos/nf-core/modules/git/blobs/0d5afc23ba44d44a805c35902febc0a382b17651'
            }
        """
        results = {}
        for f in self.modules_file_tree:
            if not f["path"].startswith("software/{}".format(module)):
                continue
            if f["type"] != "blob":
                continue
            if "/test/" in f["path"]:
                continue
            results[f["path"]] = f["url"]
        return results

    def download_gh_file(self, dl_filename, api_url):
        """Download a file from GitHub using the GitHub API

        Args:
            dl_filename (string): Path to save file to
            api_url (string): GitHub API URL for file

        Raises:
            If a problem, raises an error
        """

        # Make target directory if it doesn't already exist
        dl_directory = os.path.dirname(dl_filename)
        if not os.path.exists(dl_directory):
            os.makedirs(dl_directory)

        # Call the GitHub API
        r = requests.get(api_url)
        if r.status_code != 200:
            raise SystemError("Could not fetch {} file: {}\n {}".format(self.modules_repo.name, r.status_code, api_url))
        result = r.json()
        file_contents = base64.b64decode(result["content"])

        # Write the file contents
        with open(dl_filename, "wb") as fh:
            fh.write(file_contents)

    def has_valid_pipeline(self):
        """Check that we were given a pipeline"""
        if self.pipeline_dir is None or not os.path.exists(self.pipeline_dir):
            log.error("Could not find pipeline: {}".format(self.pipeline_dir))
            return False
        main_nf = os.path.join(self.pipeline_dir, "main.nf")
        nf_config = os.path.join(self.pipeline_dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            log.error("Could not find a main.nf or nextfow.config file in: {}".format(self.pipeline_dir))
            return False


class ModulesTestHelper(object):
    def __init__(
        self,
        module_name,
        run_test=False,
        test_yml_output_path=None,
        force_overwrite=False,
        no_prompts=False,
    ):
        self.module_name = module_name
        self.run_test = run_test
        self.test_yml_output_path = test_yml_output_path
        self.force_overwrite = force_overwrite
        self.no_prompts = no_prompts
        self.module_dir = os.path.join("software", *module_name.split("/"))
        self.module_test_main = os.path.join("tests", "software", *module_name.split("/"), "main.nf")
        self.entry_points = []
        self.tests = []

    def run(self):
        """ Run build steps """
        self.check_inputs()
        self.scrape_workflow_entry_points()
        self.build_all_tests()
        self.print_test_yml()

    def check_inputs(self):
        """ Do more complex checks about supplied flags. """
        # First, sanity check that the module directory exists
        if not os.path.isdir(self.module_dir):
            raise UserWarning(f"Cannot find directory '{self.module_dir}'. Should be TOOL/SUBTOOL or TOOL")
        if not os.path.exists(self.module_test_main):
            raise UserWarning(f"Cannot find module test workflow '{self.module_dir}/main.nf'")

        # Check that we're running tests if no prompts
        if not self.run_test and self.no_prompts:
            raise UserWarning(f"Must run tests if not using prompts. Please use '--run-test --no-prompts'")

        # Get the output YAML file / check it does not already exist
        while self.test_yml_output_path is None:
            default_val = f"tests/software/{self.module_name}/test.yml"
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
        """ Find the test workflow entry points from main.nf """
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
        if not self.no_prompts:
            log.info(
                "[yellow]Press enter to use default values [cyan bold](shown in brackets) [yellow]or type your own responses"
            )

        for entry_point in self.entry_points:
            ep_test = self.build_single_test(entry_point)
            if ep_test:
                self.tests.append(ep_test)

    def build_single_test(self, entry_point):
        """Given the supplied cli flags, prompt for any that are missing.

        Returns: False if failure, None if success.
        """
        ep_test = {
            "name": "",
            "command": "",
            "tags": [],
            "files": [],
        }

        print("\n")
        log.info(f"Building test meta for entry point '{entry_point}'")

        while ep_test["name"] == "":
            default_val = f"Run tests for {self.module_name} - {entry_point}"
            if self.no_prompts:
                ep_test["name"] = default_val
            else:
                ep_test["name"] = rich.prompt.Prompt.ask("[violet]Test name", default=default_val).strip()

        while ep_test["command"] == "":
            default_val = (
                f"nextflow run tests/software/{self.module_name} -entry {entry_point} -c tests/config/nextflow.config"
            )
            if self.no_prompts:
                ep_test["command"] = default_val
            else:
                ep_test["command"] = rich.prompt.Prompt.ask("[violet]Test command", default=default_val).strip()

        while len(ep_test["tags"]) == 0:
            mod_name_parts = self.module_name.split("/")
            tag_defaults = []
            for idx in range(0, len(mod_name_parts)):
                tag_defaults.append("_".join(mod_name_parts[: idx + 1]))
            tag_defaults.append(entry_point.replace("test_", ""))
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

    def get_md5_sums(self, entry_point, command):
        """
        Recursively go through directories and subdirectories
        and generate tuples of (<file_path>, <md5sum>)
        returns: list of tuples
        """
        if self.run_test:
            results_dir = self.run_test_workflow(command)
        else:
            results_dir = None
            while results_dir is None:
                results_dir = rich.prompt.Prompt.ask(f"[violet]Results folder for test with this entry-point")
                if not os.path.isdir(results_dir):
                    log.error(f"Directory '{results_dir}' does not exist")
                    results_dir = None

        test_files = []
        for root, dir, file in os.walk(results_dir):
            for elem in file:
                elem = os.path.join(root, elem)
                elem_md5 = self._md5(elem)
                # Switch out the temporary directory with the expected 'output' directory
                if self.run_test:
                    elem = elem.replace(results_dir, "output")
                test_files.append({"path": elem, "md5sum": elem_md5})

        if len(test_files) == 0:
            raise UserWarning(f"Could not find any test result files in '{results_dir}'")

        return test_files

    def run_test_workflow(self, command):
        """ Given a test workflow and an entry point, run the test workflow """

        # The config expects $PROFILE and Nextflow fails if it's not set
        if os.environ.get("PROFILE") is None:
            log.debug("Setting env var '$PROFILE' to an empty string as not set")
            os.environ["PROFILE"] = ""

        tmp_dir = tempfile.mkdtemp()
        command += f" --outdir {tmp_dir}"

        log.info(f"Running '{self.module_name}' test with command:\n[violet]{command}")
        try:
            nfconfig_raw = subprocess.check_output(shlex.split(command))
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise AssertionError(
                    "It looks like Nextflow is not installed. It is required for most nf-core functions."
                )
        except subprocess.CalledProcessError as e:
            raise UserWarning(f"Error running test workflow (exit code {e.returncode})\n[red]{e.output.decode()}")
        else:
            log.info("Test workflow worked")
            log.debug(nfconfig_raw)

        return tmp_dir

    def print_test_yml(self):
        """
        Generate the test yml file.
        """

        # Tweak YAML output
        class CustomDumper(yaml.Dumper):
            def represent_dict_preserve_order(self, data):
                """Add custom dumper class to prevent overwriting the global state
                This prevents yaml from changing the output order

                See https://stackoverflow.com/a/52621703/1497385
                """
                return self.represent_dict(data.items())

            def increase_indent(self, flow=False, *args, **kwargs):
                """Indent YAML lists so that YAML validates with Prettier

                See https://github.com/yaml/pyyaml/issues/234#issuecomment-765894586
                """
                return super().increase_indent(flow=flow, indentless=False)

        CustomDumper.add_representer(dict, CustomDumper.represent_dict_preserve_order)

        if self.test_yml_output_path == "-":
            console = Console()
            yaml_str = yaml.dump(self.tests, Dumper=CustomDumper)
            console.print("\n", Syntax(yaml_str, "yaml"), "\n")
            return

        try:
            log.info(f"Writing to '{self.test_yml_output_path}'")
            with open(self.test_yml_output_path, "w") as fh:
                yaml.dump(self.tests, fh, Dumper=CustomDumper)
        except FileNotFoundError as e:
            raise UserWarning("Could not create test.yml file: '{}'".format(e))
