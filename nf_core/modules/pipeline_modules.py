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
from .module_utils import create_modules_json, get_module_git_log, prompt_module_version_sha
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


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

    def install(self, module=None, latest=False):

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the available modules
        self.modules_repo.get_modules_file_tree()

        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.modules_repo.modules_avail_module_names,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
        if latest:
            # Fetch the latest commit for the module
            version = get_module_git_log(module, per_page=1, page_nbr=1)[0]["git_sha"]
        else:
            try:
                version = prompt_module_version_sha(module)
            except SystemError as e:
                log.error(e)
                sys.exit(1)
        log.info("Installing {}".format(module))

        # Check that the supplied name is an available module
        if module not in self.modules_repo.modules_avail_module_names:
            log.error("Module '{}' not found in list of available modules.".format(module))
            log.info("Use the command 'nf-core modules list' to view available software")
            return False
        log.debug("Installing module '{}' at modules hash {}".format(module, self.modules_repo.modules_current_hash))

        # Set the install folder based on the repository name
        install_folder = ["nf-core", "software"]
        if not self.modules_repo.name == "nf-core/modules":
            install_folder = ["external"]

        # Check that we don't already have a folder for this module
        module_dir = os.path.join(self.pipeline_dir, "modules", *install_folder, module)
        if os.path.exists(module_dir):
            log.error("Module directory already exists: {}".format(module_dir))
            # TODO: uncomment next line once update is implemented
            # log.info("To update an existing module, use the commands 'nf-core update'")
            return False

        # Download module files
        files = self.modules_repo.get_module_file_urls(module, version)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            split_filename = filename.split("/")
            dl_filename = os.path.join(self.pipeline_dir, "modules", *install_folder, *split_filename[1:])
            self.modules_repo.download_gh_file(dl_filename, api_url)
        log.info("Downloaded {} files to {}".format(len(files), module_dir))

        # Update module.json with new module
        modules_json_path = os.path.join(self.pipeline_dir, "modules.json")
        with open(modules_json_path, "r") as fh:
            modules_json = json.load(fh)

        modules_json["modules"][module] = {"git_sha": version}
        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=4)
        return True

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

        # Set the install folder based on the repository name
        install_folder = ["nf-core", "software"]
        if not self.modules_repo.name == "nf-core/modules":
            install_folder = ["external"]

        # Get the module directory
        module_dir = os.path.join(self.pipeline_dir, "modules", *install_folder, module)

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
        """Get list of modules installed in the current pipeline"""
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
        self.has_modules_file()
        return True

    def has_modules_file(self):
        """Checks whether a module.json file has been created and creates one if it is missing"""
        modules_json_path = os.path.join(self.pipeline_dir, "modules.json")
        if not os.path.exists(modules_json_path):
            log.info("Creating missing 'module.json' file.")
            create_modules_json(self.pipeline_dir)
