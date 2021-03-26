#!/usr/bin/env python
"""
Code to handle several functions in order to deal with nf-core/modules in
nf-core pipelines

* list modules
* install modules
* remove modules
* update modules (TODO)
*
"""

from __future__ import print_function
import base64
import glob
import json
import logging
import os
import re
import hashlib
import questionary
import requests
import rich
import shutil
import yaml
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
import rich
from nf_core.utils import rich_force_colors
from nf_core.lint.pipeline_todos import pipeline_todos
import sys

import nf_core.utils

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
        self.modules_file_tree = {}
        self.modules_current_hash = None
        self.modules_avail_module_names = []

    def get_modules_file_tree(self):
        """
        Fetch the file list from the repo, using the GitHub API

        Sets self.modules_file_tree
             self.modules_current_hash
             self.modules_avail_module_names
        """
        api_url = "https://api.github.com/repos/{}/git/trees/{}?recursive=1".format(self.name, self.branch)
        r = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
        if r.status_code == 404:
            log.error("Repository / branch not found: {} ({})\n{}".format(self.name, self.branch, api_url))
            sys.exit(1)
        elif r.status_code != 200:
            raise SystemError(
                "Could not fetch {} ({}) tree: {}\n{}".format(self.name, self.branch, r.status_code, api_url)
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
        r = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
        if r.status_code != 200:
            raise SystemError("Could not fetch {} file: {}\n {}".format(self.name, r.status_code, api_url))
        result = r.json()
        file_contents = base64.b64decode(result["content"])

        # Write the file contents
        with open(dl_filename, "wb") as fh:
            fh.write(file_contents)


class PipelineModules(object):
    def __init__(self):
        """
        Initialise the PipelineModules object
        """
        self.modules_repo = ModulesRepo()
        self.pipeline_dir = None
        self.pipeline_module_names = []

    def list_modules(self, print_json=False):
        """
        Get available module names from GitHub tree for repo
        and print as list to stdout
        """

        # Initialise rich table
        table = rich.table.Table()
        table.add_column("Module Name")
        modules = []

        # No pipeline given - show all remote
        if self.pipeline_dir is None:
            log.info(f"Modules available from {self.modules_repo.name} ({self.modules_repo.branch}):\n")

            # Get the list of available modules
            self.modules_repo.get_modules_file_tree()
            modules = self.modules_repo.modules_avail_module_names
            # Nothing found
            if len(modules) == 0:
                log.info(f"No available modules found in {self.modules_repo.name} ({self.modules_repo.branch})")
                return ""

        # We have a pipeline - list what's installed
        else:
            log.info(f"Modules installed in '{self.pipeline_dir}':\n")

            # Check whether pipelines is valid
            try:
                self.has_valid_pipeline()
            except UserWarning as e:
                log.error(e)
                return ""
            # Get installed modules
            self.get_pipeline_modules()
            modules = self.pipeline_module_names
            # Nothing found
            if len(modules) == 0:
                log.info(f"No nf-core modules found in '{self.pipeline_dir}'")
                return ""

        for mod in sorted(modules):
            table.add_row(mod)
        if print_json:
            return json.dumps(modules, sort_keys=True, indent=4)
        return table

    def install(self, module=None):

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the available modules
        self.modules_repo.get_modules_file_tree()

        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.modules_repo.modules_avail_module_names,
                style=nf_core.utils.nfcore_question_style,
            ).ask()

        log.info("Installing {}".format(module))

        # Check that the supplied name is an available module
        if module not in self.modules_repo.modules_avail_module_names:
            log.error("Module '{}' not found in list of available modules.".format(module))
            log.info("Use the command 'nf-core modules list' to view available software")
            return False
        log.debug("Installing module '{}' at modules hash {}".format(module, self.modules_repo.modules_current_hash))

        # Check that we don't already have a folder for this module
        module_dir = os.path.join(self.pipeline_dir, "modules", "nf-core", "software", module)
        if os.path.exists(module_dir):
            log.error("Module directory already exists: {}".format(module_dir))
            # TODO: uncomment next line once update is implemented
            # log.info("To update an existing module, use the commands 'nf-core update'")
            return False

        # Download module files
        files = self.modules_repo.get_module_file_urls(module)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            dl_filename = os.path.join(self.pipeline_dir, "modules", "nf-core", filename)
            self.modules_repo.download_gh_file(dl_filename, api_url)
        log.info("Downloaded {} files to {}".format(len(files), module_dir))

    def update(self, module, force=False):
        log.error("This command is not yet implemented")
        pass

    def remove(self, module):
        """
        Remove an already installed module
        This command only works for modules that are installed from 'nf-core/modules'
        """

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the installed modules
        self.get_pipeline_modules()

        if module is None:
            if len(self.pipeline_module_names) == 0:
                log.error("No installed modules found in pipeline")
                return False
            module = questionary.autocomplete(
                "Tool name:", choices=self.pipeline_module_names, style=nf_core.utils.nfcore_question_style
            ).ask()

        # Get the module directory
        module_dir = os.path.join(self.pipeline_dir, "modules", "nf-core", "software", module)

        # Verify that the module is actually installed
        if not os.path.exists(module_dir):
            log.error("Module directory is not installed: {}".format(module_dir))
            log.info("The module you want to remove does not seem to be installed")
            return False

        log.info("Removing {}".format(module))

        # Remove the module
        try:
            shutil.rmtree(module_dir)
            # Try cleaning up empty parent if tool/subtool and tool/ is empty
            if module.count("/") > 0:
                parent_dir = os.path.dirname(module_dir)
                try:
                    os.rmdir(parent_dir)
                except OSError:
                    log.debug(f"Parent directory not empty: '{parent_dir}'")
                else:
                    log.debug(f"Deleted orphan tool directory: '{parent_dir}'")
            log.info("Successfully removed {} module".format(module))
            return True
        except OSError as e:
            log.error("Could not remove module: {}".format(e))
            return False

    def get_pipeline_modules(self):
        """ Get list of modules installed in the current pipeline """
        self.pipeline_module_names = []
        module_mains = glob.glob(f"{self.pipeline_dir}/modules/nf-core/software/**/main.nf", recursive=True)
        for mod in module_mains:
            self.pipeline_module_names.append(
                os.path.dirname(os.path.relpath(mod, f"{self.pipeline_dir}/modules/nf-core/software/"))
            )

    def has_valid_pipeline(self):
        """Check that we were given a pipeline"""
        if self.pipeline_dir is None or not os.path.exists(self.pipeline_dir):
            log.error("Could not find pipeline: {}".format(self.pipeline_dir))
            return False
        main_nf = os.path.join(self.pipeline_dir, "main.nf")
        nf_config = os.path.join(self.pipeline_dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            raise UserWarning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.pipeline_dir}'")
