#!/usr/bin/env python
"""
Code to handle DSL2 module imports from a GitHub repository
"""

from __future__ import print_function
from rich.console import Console
from rich.syntax import Syntax

import base64
import hashlib
import logging
import os
import requests
import rich
import shutil
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
        test_name=None,
        test_command=None,
        test_tags=[],
        test_input_results_dir=None,
        run_test=False,
        test_yml_output_path=None,
        force_overwrite=False,
        no_prompts=False,
    ):
        self.module_name = module_name
        self.test_input_results_dir = test_input_results_dir
        self.run_test = run_test
        self.test_yml_output_path = test_yml_output_path
        self.force_overwrite = force_overwrite
        self.no_prompts = no_prompts
        self.modules_dir = os.path.join("software", *module_name.split("/"))
        self.test_yaml = {
            "name": test_name,
            "command": test_command,
            "tags": test_tags,
            "files": [],
        }

    def run(self):
        """ Run build steps """
        self.check_inputs()
        self.get_md5_sums()
        self.build_test_yaml()
        self.print_test_yml()

    def check_inputs(self):
        """ Do more complex checks about supplied flags. """
        # First, sanity check that the module directory exists
        if not os.path.isdir(self.modules_dir):
            raise UserWarning(f"Cannot find directory '{self.modules_dir}'. Should be TOOL/SUBTOOL or TOOL")
        if not os.path.exists(os.path.join(self.modules_dir, "main.nf")):
            raise UserWarning(f"Cannot find module file '{self.modules_dir}/main.nf'")

        # Sanity check + assign test run flags
        if self.run_test and self.test_input_results_dir is not None:
            raise UserWarning(f"Either supply '--input' or '--run-test', not both")
        if not self.run_test and self.test_input_results_dir is None:
            raise UserWarning(
                f"Either supply a test output directory with '--input' or trigger a run with '--run-test'"
            )

        # Check that the output YAML file does not already exist
        if (
            self.test_yml_output_path is not None
            and os.path.exists(self.test_yml_output_path)
            and not self.force_overwrite
        ):
            raise UserWarning(
                f"Test YAML file already exists! '{self.test_yml_output_path}'. Use '--force' to overwrite."
            )

    def build_test_yaml(self):
        """Given the supplied cli flags, prompt for any that are missing.

        Returns: False if failure, None if success.
        """

        # Prompt for missing values
        if (
            any([x is None for x in [self.test_yaml["name"], self.test_yaml["command"], self.test_yml_output_path]])
            or len(self.test_yaml["tags"]) == 0
        ):
            if not self.no_prompts:
                log.info("[green]Press enter to use default values [cyan bold](shown in brackets)")

        while self.test_yaml["name"] is None:
            default_val = f"Run tests for {self.module_name}"
            if self.no_prompts:
                self.test_yaml["name"] = default_val
            else:
                self.test_yaml["name"] = rich.prompt.Prompt.ask("[violet]Test name", default=default_val).strip()
                if self.test_yaml["name"] == "":
                    self.test_yaml["name"] = None

        while self.test_yaml["command"] is None:
            default_val = f"nextflow run tests/software/{self.module_name} -c tests/config/nextflow.config"
            if self.no_prompts:
                self.test_yaml["command"] = default_val
            else:
                self.test_yaml["command"] = rich.prompt.Prompt.ask("[violet]Test command", default=default_val).strip()
                if self.test_yaml["command"] == "":
                    self.test_yaml["name"] = None

        while len(self.test_yaml["tags"]) == 0:
            mod_name_parts = self.module_name.split("/")
            tag_defaults = []
            for idx in range(0, len(mod_name_parts)):
                tag_defaults.append("_".join(mod_name_parts[: idx + 1]))
            if self.no_prompts:
                self.test_yaml["tags"] = tag_defaults
            else:
                tags_str = ""
                while tags_str == "":
                    tags_str = rich.prompt.Prompt.ask(
                        "[violet]Test tags[/] (comma separated)", default=",".join(tag_defaults)
                    ).strip()
                self.test_yaml["tags"] = [t.strip() for t in tags_str.split(",")]

        while self.test_yml_output_path is None:
            default_val = f"tests/software/{self.module_name}/test.yml"
            if self.no_prompts:
                self.test_yml_output_path = default_val
                if os.path.exists(self.test_yml_output_path) and not self.force_overwrite:
                    raise UserWarning(
                        f"Test YAML file already exists! '{self.test_yml_output_path}'. Use '--force' to overwrite."
                    )
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

        self.test_yaml["name"] = self.test_yaml["name"]
        self.test_yaml["command"] = self.test_yaml["command"]
        self.test_yaml["tags"] = self.test_yaml["tags"]

    def _md5(self, fname):
        """Generate md5 sum for file"""
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        md5sum = hash_md5.hexdigest()
        return md5sum

    def get_md5_sums(self):
        """
        Recursively go through directories and subdirectories
        and generate tuples of (<file_path>, <md5sum>)
        returns: list of tuples
        """
        for root, dir, file in os.walk(self.test_input_results_dir):
            for elem in file:
                elem = os.path.join(root, elem)
                elem_md5 = self._md5(elem)
                self.test_yaml["files"].append({"path": elem, "md5sum": elem_md5})

        if len(self.test_yaml["files"]) == 0:
            raise UserWarning(f"Could not find any test result files in '{self.test_input_results_dir}'")

    def print_test_yml(self):
        """
        Generate the test yml file.

        NB: Results dict is wrapped in a list!
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
            yaml_str = yaml.dump([self.test_yaml], Dumper=CustomDumper)
            console.print("\n", Syntax(yaml_str, "yaml"), "\n")
            return

        try:
            log.info(f"Writing to '{self.test_yml_output_path}'")
            with open(self.test_yml_output_path, "w") as fh:
                yaml.dump([self.test_yaml], fh, Dumper=CustomDumper)
        except FileNotFoundError as e:
            raise UserWarning("Could not create test.yml file: '{}'".format(e))
