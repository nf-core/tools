#!/usr/bin/env python
"""
Code to handle DSL2 module imports from a GitHub repository
"""

from __future__ import print_function
import base64
import logging
import os
import re
import hashlib
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
from nf_core.lint.pipeline_todos import pipeline_todos

log = logging.getLogger(__name__)


class ModuleLintException(Exception):
    """Exception raised when there was an error with module linting"""

    pass


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

    def lint(self, module=None, print_results=True, show_passed=False, local=False):
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
        if module:
            local_modules = []
            nfcore_modules_names = [m.module_name for m in nfcore_modules]
            try:
                idx = nfcore_modules_names.index(module)
                nfcore_modules = [nfcore_modules[idx]]
            except ValueError as e:
                raise ModuleLintException("Could not find the specified module: {}".format(module))

        log.info(f"Linting pipeline: [magenta]{self.dir}")
        if module:
            log.info(f"Linting module: [magenta]{module}")

        # Lint local modules
        if local and len(local_modules) > 0:
            self.lint_local_modules(local_modules)

        # Lint nf-core modules
        if len(nfcore_modules) > 0:
            self.lint_nfcore_modules(nfcore_modules)

            self.check_module_changes(nfcore_modules)

        if print_results:
            self._print_results(show_passed=show_passed)

        return {"passed": self.passed, "warned": self.warned, "failed": self.failed}

    def lint_local_modules(self, local_modules):
        """
        Lint a local module
        Only issues warnings instead of failures
        """
        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                "Linting local modules", total=len(local_modules), test_name=os.path.basename(local_modules[0])
            )

            for mod in local_modules:
                progress_bar.update(lint_progress, advance=1, test_name=os.path.basename(mod))
                mod_object = NFCoreModule(
                    module_dir=mod, base_dir=self.dir, repo_type=self.repo_type, nf_core_module=False
                )
                mod_object.main_nf = mod
                mod_object.module_name = os.path.basename(mod)
                mod_object.lint_main_nf()
                self.warned += mod_object.warned + mod_object.failed
                self.passed += mod_object.passed

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

        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                "Linting nf-core modules", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
            )
            for mod in nfcore_modules:
                if "TOOL/SUBTOOL" in mod.module_dir:
                    continue
                progress_bar.update(lint_progress, advance=1, test_name=mod.module_name)
                passed, warned, failed = mod.lint()
                self.passed += passed
                self.warned += warned
                self.failed += failed

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
            if os.path.exists(local_modules_dir):
                local_modules = os.listdir(local_modules_dir)
                local_modules = [x for x in local_modules if (x.endswith(".nf") and not x == "functions.nf")]

        # nf-core/modules
        if self.repo_type == "modules":
            nfcore_modules_dir = os.path.join(self.dir, "software")

        # Get nf-core modules
        if os.path.exists(nfcore_modules_dir):
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

        # Make full (relative) file paths and create NFCoreModule objects
        local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]
        nfcore_modules = [
            NFCoreModule(os.path.join(nfcore_modules_dir, m), repo_type=self.repo_type, base_dir=self.dir)
            for m in nfcore_modules
        ]

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

    def get_sha(self, file):
        """ Calcualte the SHA256 sum for a file """
        sha_hash = hashlib.sha1()
        with open(file, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha_hash.update(byte_block)
        return sha_hash.hexdigest()

    def check_module_changes(self, nfcore_modules):
        """
        Checks whether installed nf-core modules have changed compared to the
        original repository
        """
        passed = []
        failed = []

        pipeline_modules = PipelineModules()
        pipeline_modules.pipeline_dir = self.dir
        pipeline_modules.get_modules_file_tree()

        # Compare sha sums for files
        for mod in nfcore_modules:
            # for testing
            if mod.module_name == "pangolin":
                print(mod.module_name)
                # check main.nf
                main_nf_sha = self.get_sha(os.path.join(mod.module_dir, "main.nf"))
                files = pipeline_modules.get_module_file_urls(mod.module_name)
                for filename, api_url in files.items():
                    # Call the GitHub API
                    r = requests.get(api_url)
                    if r.status_code != 200:
                        raise SystemError(
                            "Could not fetch {} file: {}\n {}".format(self.modules_repo.name, r.status_code, api_url)
                        )
                    result = r.json()
                    file_contents = base64.b64decode(result["content"])

        return {"passed": passed, "failed": failed}


class NFCoreModule(object):
    """
    A class to hold the information a bout a nf-core module
    Includes functionality for lintislng
    """

    def __init__(self, module_dir, repo_type, base_dir, nf_core_module=True):
        self.module_dir = module_dir
        self.repo_type = repo_type
        self.base_dir = base_dir
        self.passed = []
        self.warned = []
        self.failed = []
        self.inputs = []
        self.outputs = []

        if nf_core_module:
            # Initialize the important files
            self.main_nf = os.path.join(self.module_dir, "main.nf")
            self.meta_yml = os.path.join(self.module_dir, "meta.yml")
            self.function_nf = os.path.join(self.module_dir, "functions.nf")
            self.software = self.module_dir.split("software" + os.sep)[1]
            self.test_dir = os.path.join(self.base_dir, "tests", "software", self.software)
            self.module_name = module_dir.split("software" + os.sep)[1]

    def lint(self):
        """ Perform linting on this module """
        # Iterate over modules and run all checks on them

        # Lint the main.nf file
        self.lint_main_nf()

        # Lint the meta.yml file
        self.lint_meta_yml()

        # Lint the functions.nf file
        self.lint_functions_nf()

        # Lint the tests
        if self.repo_type == "modules":
            self.lint_module_tests()

        # Check for TODOs
        self.wf_path = self.module_dir
        self.warned += pipeline_todos(self)["warned"]

        return self.passed, self.warned, self.failed

    def lint_module_tests(self):
        """ Lint module tests """

        if os.path.exists(self.test_dir):
            self.passed.append("Test directory exsists for {}".format(self.software))
        else:
            self.failed.append("Test directory is missing for {}: {}".format(self.software, self.test_dir))
            return

        # Lint the test main.nf file
        test_main_nf = os.path.join(self.test_dir, "main.nf")
        if os.path.exists(test_main_nf):
            self.passed.append("test main.nf exists for {}".format(self.software))
        else:
            self.failed.append("test main.nf doesn't exist for {}".format(self.software))

        # Lint the test.yml file
        test_yml_file = os.path.join(self.test_dir, "test.yml")
        try:
            with open(test_yml_file, "r") as fh:
                test_yml = yaml.safe_load(fh)
            self.passed.append("test.yml exists for {}".format(self.software))
        except FileNotFoundError:
            self.failed.append("test.yml doesn't exist for {}".format(self.software))

    def lint_meta_yml(self):
        """ Lint a meta yml file """
        required_keys = ["params", "input", "output"]
        try:
            with open(self.meta_yml, "r") as fh:
                meta_yaml = yaml.safe_load(fh)
            self.passed.append("meta.yml exists {}".format(self.meta_yml))
        except FileNotFoundError:
            self.failed.append("meta.yml doesn't exist for {} ({})".format(self.module_name, self.meta_yml))
            return

        # Confirm that all required keys are given
        contains_required_keys = True
        for rk in required_keys:
            if not rk in meta_yaml.keys():
                self.failed.append("{} not specified in {}".format(rk, self.meta_yml))
                contains_required_keys = False
        if contains_required_keys:
            self.passed.append("{} contains all required keys".format(self.meta_yml))

        # Confirm that all input and output channels are specified
        meta_input = [list(x.keys())[0] for x in meta_yaml["input"]]
        for input in self.inputs:
            if input in meta_input:
                self.passed.append("{} specified for {}".format(input, self.module_name))
            else:
                self.failed.append("{} missing in meta.yml for {}".format(input, self.module_name))

        meta_output = [list(x.keys())[0] for x in meta_yaml["output"]]
        for output in self.outputs:
            if output in meta_output:
                self.passed.append("{} specified for {}".format(output, self.module_name))
            else:
                self.failed.append("{} missing in meta.yml for {}".format(output, self.module_name))

        # confirm that the name matches the process name in main.nf
        if meta_yaml["name"].upper() == self.process_name:
            self.passed.append("Correct name specified in meta.yml: ".format(self.meta_yml))
        else:
            self.failed.append("Name in meta.yml doesn't match process name in main.nf: ".format(self.meta_yml))

    def lint_main_nf(self):
        """
        Lint a single main.nf module file
        Can also be used to lint local module files,
        in which case failures should be interpreted
        as warnings
        """
        inputs = []
        outputs = []

        # Check whether file exists and load it
        try:
            with open(self.main_nf, "r") as fh:
                lines = fh.readlines()
            self.passed.append("Module file exists {}".format(self.main_nf))
        except FileNotFoundError as e:
            self.failed.append("Module file doesn't exist {}".format(self.main_nf))
            return

        # Check that options are defined
        initoptions_re = re.compile(r"\s*def\s+options\s*=\s*initOptions\s*\(\s*params\.options\s*\)\s*")
        paramsoptions_re = re.compile(r"\s*params\.options\s*=\s*\[:\]\s*")
        if any(initoptions_re.match(l) for l in lines) and any(paramsoptions_re.match(l) for l in lines):
            self.passed.append("options specified in {}".format(self.main_nf))
        else:
            self.warned.append("options not specified in {}".format(self.main_nf))

        # Go through module main.nf file and switch state according to current section
        # Perform section-specific linting
        state = "module"
        process_lines = []
        script_lines = []
        for l in lines:
            if re.search("^\s*process\s*\w*\s*{", l) and state == "module":
                state = "process"
            if re.search("input\s*:", l) and state == "process":
                state = "input"
                continue
            if re.search("output\s*:", l) and state == "input":
                state = "output"
                continue
            if re.search("script\s*:", l) and state == "output":
                state = "script"
                continue

            # Perform state-specific linting checks
            if state == "process" and not self._is_empty(l):
                process_lines.append(l)
            if state == "input" and not self._is_empty(l):
                inputs += self._parse_input(l)
            if state == "output" and not self._is_empty(l):
                outputs += self._parse_output(l)
                outputs = list(set(outputs))  # remove duplicate 'meta's
            if state == "script" and not self._is_empty(l):
                script_lines.append(l)

        # Check the process definitions
        if self.check_process_section(process_lines):
            self.passed.append("Matching build versions in {}".format(self.main_nf))
        else:
            self.failed.append("Build versions are not matching: {}".format(self.main_nf))

        # Check the script definition
        self.check_script_section(script_lines)

        # Check whether 'meta' is emitted when given as input
        if "meta" in inputs:
            if "meta" in outputs:
                self.passed.append("'meta' emitted in {}".format(self.main_nf))
            else:
                self.failed.append("'meta' given as input but not emitted in {}".format(self.main_nf))

            # if meta is specified, it should also be used as 'saveAs ... publishId:meta.id'
            save_as = [pl for pl in process_lines if "saveAs" in pl]
            if len(save_as) > 0 and re.search("\s*publish_id\s*:\s*meta.id", save_as[0]):
                self.passed.append("'meta.id' used in saveAs function for {}".format(self.module_name))
            else:
                self.failed.append(
                    "'meta.id' specified but not used in saveAs function for {}".format(self.module_name)
                )

        # Check that a software version is emitted
        if "version" in outputs:
            self.passed.append("Module emits software version: {}".format(self.main_nf))
        else:
            self.failed.append("Module doesn't emit  software version {}".format(self.main_nf))

        return inputs, outputs

    def check_script_section(self, lines):
        """
        Lint the script section
        Checks whether 'def sotware' and 'def prefix' are defined
        """
        script = "".join(lines)

        # check for software
        if re.search("\s*def\s*software\s*=\s*getSoftwareName", script):
            self.passed.append("Software version specified in script section: {}".format(self.module_name))
        else:
            self.failed.append("Software version not specified in script section: {}".format(self.module_name))

        # check for prefix
        if re.search("\s*def\s*prefix\s*=\s*options.suffix", script):
            self.passed.append("prefix specified in script section: {}".format(self.module_name))
        else:
            self.failed.append("prefix not specified in script section: {}".format(self.module_name))

    def check_process_section(self, lines):
        """
        Lint the section of a module between the process definition
        and the 'input:' definition
        Specifically checks for correct software versions
        and containers
        """
        # Checks that build numbers of bioconda, singularity and docker container are matching
        build_id = "build"
        singularity_tag = "singularity"
        docker_tag = "docker"
        bioconda_packages = []

        # Process name should be all capital letters
        self.process_name = lines[0].split()[1]
        if all([x.upper() for x in self.process_name]):
            self.passed.append("Process name is in capital letters: {}".format(self.module_name))
        else:
            self.failed.append("Process name is not in captial letters: {}".format(self.module_name))

        # Check that process labels are correct
        correct_process_labels = ["process_low", "process_medium", "process_high", "process_long"]
        process_label = [l for l in lines if "label" in l]
        if len(process_label) > 0:
            process_label = process_label[0].split()[1].strip().strip("'").strip('"')
            if not process_label in correct_process_labels:
                self.warned.append(
                    "Process label ({}) is not among standard labels: {}".format(process_label, correct_process_labels)
                )
            else:
                self.passed.append("Correct process label for {}".format(self.module_name))
        else:
            self.warned.append("No process label specified for {}".format(self.module_name))

        for l in lines:
            if re.search("bioconda::", l):
                bioconda_packages = [b for b in l.split() if "bioconda::" in b]
                bioconda = bioconda_packages[
                    0
                ]  # use the first bioconda package to check against conatiners if not mulled
                build_id = bioconda.split("::")[1].replace('"', "").replace("'", "").split("=")[-1].strip()
            if re.search("org/singularity", l):
                singularity_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()
            if re.search("biocontainers", l):
                docker_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()

        # If it's a mulled container, just compare singularity and docker tags
        if any("mulled" in l for l in lines):
            build_id = docker_tag

        # Check that all bioconda packages have build numbers
        # Also check for newer versions
        all_packages_have_build_numbers = True
        for bp in bioconda_packages:
            if not bp.count("=") >= 2:
                all_packages_have_build_numbers = False

            # Check for correct version and newer versions
            try:
                bioconda_version = bp.split("=")[1]
                response = _bioconda_package(bp)
            except LookupError as e:
                self.warned.append(e)
            except ValueError as e:
                self.failed.append(e)
            else:
                # Check that required version is available at all
                if bioconda_version not in response.get("versions"):
                    self.failed.append("Conda dep had unknown version: {}".format(bp))
                    continue  # No need to test for latest version, continue linting
                # Check version is latest available
                last_ver = response.get("latest_version")
                if last_ver is not None and last_ver != bioconda_version:
                    self.warned.append(
                        "Bioconda version outdated: `{}`, `{}` available ({})".format(bp, last_ver, self.module_name)
                    )
                else:
                    self.passed.append("Bioconda package is the latest available: `{}`".format(bp))

        if all_packages_have_build_numbers:
            self.passed.append("All bioconda packages have build numbers in {}".format(self.module_name))
        else:
            self.failed.append("Missing build numbers for bioconda packages in {}".format(self.module_name))

        if build_id == docker_tag and build_id == singularity_tag:
            return True
        else:
            return False

    def lint_functions_nf(self):
        """
        Lint a functions.nf file
        Verifies that the file exists and contains all necessary functions
        """
        try:
            with open(self.function_nf, "r") as fh:
                lines = fh.readlines()
            self.passed.append("functions.nf exists {}".format(self.function_nf))
        except FileNotFoundError as e:
            self.failed.append("functions.nf doesn't exist {}".format(self.function_nf))
            return

        # Test whether all required functions are present
        required_functions = ["getSoftwareName", "initOptions", "getPathFromList", "saveFiles"]
        lines = "\n".join(lines)
        contains_all_functions = True
        for f in required_functions:
            if not "def " + f in lines:
                self.failed.append("functions.nf is missing '{}', {}".format(f, self.function_nf))
                contains_all_functions = False
        if contains_all_functions:
            self.passed.append("Contains all functions: {}".format(self.function_nf))

    def _parse_input(self, line):
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
            if "(" in line:
                input.append(line.split("(")[1].replace(")", ""))
            else:
                input.append(line.split()[1])
        return input

    def _parse_output(self, line):
        output = []
        if "meta" in line:
            output.append("meta")
        # TODO: should we ignore outputs without emit statement?
        if "emit" in line:
            output.append(line.split("emit:")[1].strip())

        return output

    def _is_empty(self, line):
        """ Check whether a line is empty or a comment """
        empty = False
        if line.strip().startswith("//"):
            empty = True
        if line.strip().replace(" ", "") == "":
            empty = True
        return empty


def _bioconda_package(package):
    """Query bioconda package information.

    Sends a HTTP GET request to the Anaconda remote API.

    Args:
        package (str): A bioconda package name.

    Raises:
        A LookupError, if the connection fails or times out or gives an unexpected status code
        A ValueError, if the package name can not be found (404)
    """
    dep = package.split("::")[1]
    depname = dep.split("=")[0]
    depver = dep.split("=")[1]

    anaconda_api_url = "https://api.anaconda.org/package/{}/{}".format("bioconda", depname)

    try:
        response = requests.get(anaconda_api_url, timeout=10)
    except (requests.exceptions.Timeout):
        raise LookupError("Anaconda API timed out: {}".format(anaconda_api_url))
    except (requests.exceptions.ConnectionError):
        raise LookupError("Could not connect to Anaconda API")
    else:
        if response.status_code == 200:
            return response.json()
        elif response.status_code != 404:
            raise LookupError(
                "Anaconda API returned unexpected response code `{}` for: {}\n{}".format(
                    response.status_code, anaconda_api_url, response
                )
            )
        elif response.status_code == 404:
            raise ValueError("Could not find `{}` in bioconda channel".format(package))
