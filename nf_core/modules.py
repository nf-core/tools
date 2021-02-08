#!/usr/bin/env python
"""
Code to handle DSL2 module imports from a GitHub repository
"""

from __future__ import print_function
import base64
import logging
import os
import requests
import sys
import tempfile
import shutil
import yaml
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
import rich
from nf_core.utils import rich_force_colors

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


class ModuleLint(object):
    """
    An object for linting modules either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    def __init__(self, dir):
        self.dir = dir
        self.repo_type = self.get_repo_type()
        self.passed = []
        self.warned = []
        self.failed = []

    def lint(self, module=None, print_results=True, show_passed=False):
        """
        Lint all or one specific module

        First gets a list of all local modules (in modules/local/process) and all modules
        installed from nf-core (in modules/nf-core/software)

        For all nf-core modules, the correct file structure is assured and important
        file content is verified. If directory subject to linting is a clone of 'nf-core/modules',
        the files necessary for testing the modules are also inspected.

        For all local modules, the '.nf' file is checked for some important flags, and warnings
        are issued if untypical content is found.

        :param module:          A specific module to lint
        :param print_results:   Whether to print the linting results
        :param show_passed:     Whether passed tests should be shown as well

        :returns:               dict of {passed, warned, failed}
        """

        # Get list of all modules in a pipeline
        local_modules, nfcore_modules = self.get_installed_modules()

        # Only lint the given module
        # TODO --> decide whether to implement this for local modules as well
        if module:
            local_modules = []
            nfcore_modules_names = [m.split("software" + os.sep)[1] for m in nfcore_modules]
            try:
                idx = nfcore_modules_names.index(module)
                nfcore_modules = [nfcore_modules[idx]]
            except ValueError as e:
                log.error("Could not find the given module!")
                sys.exit(1)

        # Lint local modules
        self.lint_local_modules(local_modules)

        # Lint nf-core modules
        self.lint_nfcore_modules(nfcore_modules)

        if print_results:
            self._print_results(show_passed=show_passed)

        return {"passed": self.passed, "warned": self.warned, "failed": self.failed}

    def lint_local_modules(self, local_modules):
        """
        Lint a local module
        Only issues warnings instead of failures
        """
        for mod in local_modules:
            self.lint_main_nf(mod)

    def lint_nfcore_modules(self, nfcore_modules):
        """
        Lint nf-core modules
        For each nf-core module, checks for existence of the files
        - main.nf
        - meta.yml
        - functions.nf
        And verifies that their content.

        If the linting is run for modules in the central nf-core/modules repo
        (repo_type==modules), files that are relevant for module testing are
        also examined
        """
        # Iterate over modules and run all checks on them
        for mod in nfcore_modules:
            if "SOFTWARE/TOOL" in mod:
                continue
            module_name = mod.split(os.sep)[-1]

            # Lint the main.nf file
            inputs, outputs = self.lint_main_nf(os.path.join(mod, "main.nf"))

            # Lint the functions.nf file
            self.lint_functions_nf(os.path.join(mod, "functions.nf"))

            # Lint the meta.yml file
            self.lint_meta_yml(os.path.join(mod, "meta.yml"), module_name)

            if self.repo_type == "modules":
                self.lint_module_tests(mod, module_name)

    def lint_module_tests(self, mod, module_name):
        """ Lint module tests """
        # Extract the software name
        software = mod.split("software" + os.sep)[1]
        # Check if test directory exists
        test_dir = os.path.join(self.dir, "tests", "software", software)
        if os.path.exists(test_dir):
            self.passed.append("Test directory exsists for {}".format(software))
        else:
            self.failed.append("Test directory is missing for {}: {}".format(software, test_dir))
            return

        # Lint the test main.nf file
        test_main_nf = os.path.join(test_dir, "main.nf")
        if os.path.exists(test_main_nf):
            self.passed.append("test main.nf exists for {}".format(software))
        else:
            self.failed.append("test.yml doesn't exist for {}".format(software))

        # Lint the test.yml file
        test_yml_file = os.path.join(test_dir, "test.yml")
        try:
            with open(test_yml_file, "r") as fh:
                test_yml = yaml.safe_load(fh)
            self.passed.append("test.yml exists for {}".format(software))
        except FileNotFoundError:
            self.failed.append("test.yml doesn't exist for {}".format(software))

    def lint_meta_yml(self, file, module_name):
        """ Lint a meta yml file """
        required_keys = ["name", "tools", "params", "input", "output", "authors"]
        try:
            with open(file, "r") as fh:
                meta_yaml = yaml.safe_load(fh)
            self.passed.append("meta.yml exists {}".format(file))
        except FileNotFoundError:
            self.failed.append("meta.yml doesn't exist for {} ({})".format(module_name, file))
            return

        # Confirm that all required keys are given
        contains_required_keys = True
        for rk in required_keys:
            if not rk in meta_yaml.keys():
                self.failed.append("{} not specified in {}".format(rk, file))
                contains_required_keys = False
            if contains_required_keys:
                self.passed.append("{} contains all required keys".format(file))

        # TODO --> decide whether we want/need this test? or make it silent for now
        # Check that 'name' adheres to guidelines
        software_name = file.split("software")[1].split(os.sep)[1]
        if module_name == software_name:
            required_name = module_name
        else:
            required_name = software_name + " " + module_name

        if meta_yaml["name"] == required_name:
            self.passed.append("meta.yaml module name is correct: {}".format(module_name))
        else:
            self.warned.append("meta.yaml module name not according to guidelines: {}".format(module_name))

    def lint_main_nf(self, file):
        """
        Lint a single main.nf module file
        Can also be used to lint local module files,
        in which case failures should be interpreted
        as warnings
        """
        inputs = []
        outputs = []

        def parse_input(line):
            input = []
            # more than one input
            if "tuple" in line:
                line = line.replace("tuple", "")
                line = line.replace(" ", "")
                line = line.split(",")

                for elem in line:
                    elem = elem.split("(")[1]
                    elem = elem.replace(")", "").strip()
                    input.append(elem)
            else:
                input.append(line.split()[1])
            return input

        def is_empty(line):
            empty = False
            if line.startswith("//"):
                empty = True
            if line.strip().replace(" ", "") == "":
                empty = True
            return empty

        try:
            with open(file, "r") as fh:
                lines = fh.readlines()
            self.passed.append("Module file exists {}".format(file))
        except FileNotFoundError as e:
            self.failed.append("Module file doesn't exist {}".format(file))
            return

        # Check that options are defined
        options_keywords = ["def", "options", "=", "initOptions(params.options)"]
        if any(l.split() == options_keywords for l in lines):
            self.passed.append("options specified in {}".format(file))
        else:
            self.warned.append("options not specified in {}".format(file))

        state = "module"
        for l in lines:
            # Check if state is switched
            if l.startswith("process"):
                state = "process"
            if "input:" in l:
                state = "input"
                continue
            if "output:" in l:
                state = "output"
                continue
            if "script:" in l:
                state = "script"
                continue

            # Perform state-specific linting checks
            if state == "input" and not is_empty(l):
                inputs += parse_input(l)
            if state == "output" and not is_empty(l):
                outputs.append(l.split("emit:")[1].strip())

        # Check that a software version is emitted
        if "version" in outputs:
            self.passed.append("Module emits software version: {}".format(file))
        else:
            self.failed.append("Module doesn't emit  software version {}".format(file))

        # Test for important content in the main.nf file
        # Check conda is specified
        if any("conda" in l for l in lines):
            self.passed.append("Conda environment specified in {}".format(file))
        else:
            self.warned.append("No conda environment specified in {}".format(file))

        # Check container is specified
        if any("container" in l for l in lines):
            self.passed.append("Container specified in {}".format(file))
        else:
            self.failed.append("No container specified in {}".format(file))

        return inputs, outputs

    def lint_functions_nf(self, file):
        """
        Lint a functions.nf file
        Verifies that the file exists and contains all necessary functions
        """
        try:
            with open(file, "r") as fh:
                lines = fh.readlines()
            self.passed.append("functions.nf exists {}".format(file))
        except FileNotFoundError as e:
            self.failed.append("functions.nf doesn't exist {}".format(file))
            return

        # Test whether all required functions are present
        required_functions = ["getSoftwareName", "initOptions", "getPathFromList", "saveFiles"]
        lines = "\n".join(lines)
        contains_all_functions = True
        for f in required_functions:
            if not "def " + f in lines:
                self.failed.append("functions.nf is missing '{}', {}".format(f, file))
                contains_all_functions = False
        if contains_all_functions:
            self.passed.append("Contains all functions: {}".format(file))

    def get_repo_type(self):
        """
        Determine whether this is a pipeline repository or a clone of
        nf-core/modules
        """
        # Verify that the pipeline dir exists
        if self.dir is None or not os.path.exists(self.dir):
            log.error("Could not find directory: {}".format(self.dir))
            sys.exit(1)

        # Determine repository type
        if os.path.exists(os.path.join(self.dir, "main.nf")):
            return "pipeline"
        elif os.path.exists(os.path.join(self.dir, "software")):
            return "modules"
        else:
            log.error("Could not determine repository type of {}".format(self.dir))
            sys.exit(1)

    def get_installed_modules(self):
        """
        Make a list of all modules installed in this repository

        Returns a tuple of two lists, one for local modules
        and one for nf-core modules. The local modules are represented
        as direct filepaths to the module '.nf' file.
        Nf-core module are returned as file paths to the module directories.
        In case the module contains several tools, one path to each tool directory
        is returned.

        returns (local_modules, nfcore_modules)
        """
        # initialize lists
        local_modules = []
        nfcore_modules = []
        local_modules_dir = None
        nfcore_modules_dir = os.path.join(self.dir, "modules", "nf-core", "software")

        # Get local modules
        if self.repo_type == "pipeline":
            local_modules_dir = os.path.join(self.dir, "modules", "local", "process")

            # Filter local modules
            local_modules = os.listdir(local_modules_dir)
            local_modules = [x for x in local_modules if (x.endswith(".nf") and not x == "functions.nf")]

        # nf-core/modules
        if self.repo_type == "modules":
            nfcore_modules_dir = os.path.join(self.dir, "software")

        # Get nf-core modules
        nfcore_modules_tmp = os.listdir(nfcore_modules_dir)
        nfcore_modules_tmp = [m for m in nfcore_modules_tmp if not m == "lib"]
        for m in nfcore_modules_tmp:
            m_content = os.listdir(os.path.join(nfcore_modules_dir, m))
            # Not a module, but contains sub-modules
            if not "main.nf" in m_content:
                for tool in m_content:
                    nfcore_modules.append(os.path.join(m, tool))
            else:
                nfcore_modules.append(m)

        # Make full (relative) file paths
        local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]
        nfcore_modules = [os.path.join(nfcore_modules_dir, m) for m in nfcore_modules]

        return local_modules, nfcore_modules

    def _print_results(self, show_passed=False):
        """Print linting results to the command line.

        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing final results")
        console = Console(force_terminal=rich_force_colors())

        # Helper function to format test links nicely
        def format_result(test_results, table):
            """
            Given an list of error message IDs and the message texts, return a nicely formatted
            string for the terminal with appropriate ASCII colours.
            """
            for msg in test_results:
                table.add_row(Markdown("Module lint: {}".format(msg)))
            return table

        def _s(some_list):
            if len(some_list) > 1:
                return "s"
            return ""

        # Table of passed tests
        if len(self.passed) > 0 and show_passed:
            table = Table(style="green", box=rich.box.ROUNDED)
            table.add_column(
                r"[✔] {} Test{} Passed".format(len(self.passed), _s(self.passed)),
                no_wrap=True,
            )
            table = format_result(self.passed, table)
            console.print(table)

        # Table of warning tests
        if len(self.warned) > 0:
            table = Table(style="yellow", box=rich.box.ROUNDED)
            table.add_column(r"[!] {} Test Warning{}".format(len(self.warned), _s(self.warned)), no_wrap=True)
            table = format_result(self.warned, table)
            console.print(table)

        # Table of failing tests
        if len(self.failed) > 0:
            table = Table(style="red", box=rich.box.ROUNDED)
            table.add_column(
                r"[✗] {} Test{} Failed".format(len(self.failed), _s(self.failed)),
                no_wrap=True,
            )
            table = format_result(self.failed, table)
            console.print(table)

        # Summary table
        table = Table(box=rich.box.ROUNDED)
        table.add_column("[bold green]LINT RESULTS SUMMARY".format(len(self.passed)), no_wrap=True)
        table.add_row(
            r"[✔] {:>3} Test{} Passed".format(len(self.passed), _s(self.passed)),
            style="green",
        )
        table.add_row(r"[!] {:>3} Test Warning{}".format(len(self.warned), _s(self.warned)), style="yellow")
        table.add_row(r"[✗] {:>3} Test{} Failed".format(len(self.failed), _s(self.failed)), style="red")
        console.print(table)
