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
    An object to store details about the repository being used for modules.

    Used by the `nf-core modules` top-level command with -r and -b flags,
    so that this can be used in the same way by all sucommands.
    """

    def __init__(self, dir):
        self.dir = dir
        self.get_repo_type()

    def lint(self, module=None):
        """
        Lint a module
        """

        # Get list of all modules in a pipeline
        local_modules, nfcore_modules = self.get_installed_modules()

        # Check local modules
        self.lint_local_modules(local_modules)

        # Check them nf-core modules
        results_nfcore_modules = self.lint_nfcore_modules(nfcore_modules)

    def lint_local_modules(self, local_modules):
        """
        Lint a local module
        Only issues warnings instead of failures
        """
        passed = []
        warned = []

        for mod in local_modules:
            self.lint_main_nf(mod, passed, warned)

        return {"passed": passed, "warned": warned}

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
        # TODO implement the look for test-relevant files
        passed = []
        failed = []

        # Iterate over modules and run all checks on them
        for mod in nfcore_modules:
            module_name = mod.split("/")[-1]

            # Lint the main.nf file
            main_nf = os.path.join(mod, "main.nf")
            self.lint_main_nf(main_nf, passed, failed)

            # Lint the functions file
            functions_nf = os.path.join(mod, "functions.nf")
            self.lint_functions_nf(functions_nf, passed, failed)

            # Lint the meta.yml file
            meta_yml = os.path.join(mod, "meta.yml")
            self.lint_meta_yml(meta_yml, module_name, passed, failed)

            if self.repo_type == "modules":
                self.lint_module_tests(mod, passed, failed)

        return {"passed": passed, "failed": failed}

    def lint_module_tests(self, mod, passed, failed):
        """ Lint module tests """
        # Extract the software name
        software = mod.split("software/")[1].split("/")[0]

        # Check if test directory exists
        # test_dir =

    def lint_meta_yml(self, file, module_name, passed, failed):
        """ Lint a meta yml file """
        required_keys = ["name", "tools", "params", "input", "output", "authors"]
        try:
            with open(file, "r") as fh:
                meta_yaml = yaml.safe_load(fh)
            passed.append("meta.yml exists {}".format(file))
        except FileNotFoundError:
            failed.append("meta.yml doesn't exist {}".format(file))
            return {"passed": passed, "failed": failed}

        # Confirm that all required keys are given
        for rk in required_keys:
            if rk in meta_yaml.keys():
                passed.append("{} is specified in {}".format(rk, file))
            else:
                failed.append("{} not specified in {}".format(rk, file))

        return {"passed": passed, "failed": failed}

    def lint_main_nf(self, file, passed, failed):
        """
        Lint a single main.nf module file
        Can also be used to lint local module files,
        in which case failures should be interpreted
        as warnings
        """
        conda_env = False
        container = False
        software_version = False
        try:
            with open(file, "r") as fh:
                l = fh.readline()
                while l:
                    if "conda" in l:
                        conda_env = True
                    if "container" in l:
                        container = True
                    if "emit:" in l and "version" in l:
                        software_version = True
                    l = fh.readline()
            passed.append("Module file exists {}".format(file))
        except FileNotFoundError as e:
            failed.append("Module file does'nt exist {}".format(file))
            return {"passed": passed, "failed": failed}

        if conda_env:
            passed.append("Conda environment specified in {}".format(file))
        else:
            failed.append("No conda environment specified in {}".format(file))

        if container:
            passed.append("Container specified in {}".format(file))
        else:
            failed.append("No container specified in {}".format(file))

        if software_version:
            passed.append("Module emits software version: {}".format(file))
        else:
            failed.append("Module doesn't emit  software version {}".format(file))

        return {"passed": passed, "failed": failed}

    def lint_functions_nf(self, file, passed, failed):
        """ Lint a functions.nf file """
        if os.path.exists(file):
            passed.append("functions.nf exists {}".format(file))
        else:
            failed.append("functions.nf doesn't exist {}".format(file))

        return {"passed": passed, "failed": failed}

    def get_repo_type(self):
        """
        Determine whether this is a pipeline repository or a clone of
        nf-core/modules
        """
        # Verify that the pipeline dir exists
        if self.pipeline_dir is None or not os.path.exists(self.pipeline_dir):
            log.error("Could not find pipeline: {}".format(self.pipeline_dir))
            sys.exit(1)

        # Determine repository type
        if os.path.exists(os.path.join(self.pipeline_dir, "main.nf")):
            self.repo_type = "pipeline"
        elif os.path.exists(os.path.join(self.pipeline_dir, "software")):
            self.repo_type = "modules"
        else:
            log.error("Could not determine repository type of {}".format(self.pipeline_dir))
            sys.exit(1)

    def get_installed_modules(self):
        """
        Make a list of all modules installed in this repository

        Returns a tuple of two lists, one for local modules
        and one for nfcore modules. The local modules are represented as filenames,
        while for nf-core modules the module diretories are used.

        returns (local_modules, nfcore_modules)
        """
        # pipeline repository
        local_modules = []
        local_modules_dir = None
        nfcore_modules_dir = os.path.join(self.pipeline_dir, "modules", "nf-core", "software")
        if self.repo_type == "pipeline":
            local_modules_dir = os.path.join(self.pipeline_dir, "modules", "local", "process")

            # Filter local modules
            local_modules = os.listdir(local_modules_dir)
            local_modules = [x for x in local_modules if (x.endswith(".nf") and not x == "functions.nf")]

        # nf-core/modules
        if self.repo_type == "modules":
            nfcore_modules_dir = os.path.join(self.pipeline_dir, "software")

        # Get nf-core modules
        nfcore_modules = os.listdir(nfcore_modules_dir)
        nfcore_modules = [m for m in nfcore_modules if not m == "lib"]  # omit the lib directory TODO lint that one too
        for m in nfcore_modules:
            m_content = os.listdir(os.path.join(nfcore_modules_dir, m))
            # Not a module, but contains sub-modules
            if not "main.nf" in m_content:
                for tool in m_content:
                    nfcore_modules.append(os.path.join(m, tool))
                nfcore_modules.remove(m)

        # Make full (relative) file paths
        if local_modules_dir:
            local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]
        nfcore_modules = [os.path.join(nfcore_modules_dir, m) for m in nfcore_modules]

        return local_modules, nfcore_modules
