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
        self.force = False
        self.latest = False
        self.sha = None

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
        if self.latest and self.sha is not None:
            log.error("Cannot use '--sha' and '--latest' at the same time!")
            return False

        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.modules_repo.modules_avail_module_names,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Check that the supplied name is an available module
        if module not in self.modules_repo.modules_avail_module_names:
            log.error("Module '{}' not found in list of available modules.".format(module))
            log.info("Use the command 'nf-core modules list' to view available software")
            return False
        # Set the install folder based on the repository name
        install_folder = ["nf-core", "software"]
        if not self.modules_repo.name == "nf-core/modules":
            install_folder = ["external"]

        # Compute the module directory
        module_dir = os.path.join(self.pipeline_dir, "modules", *install_folder, module)

        # Load 'modules.json'
        modules_json_path = os.path.join(self.pipeline_dir, "modules.json")
        with open(modules_json_path, "r") as fh:
            modules_json = json.load(fh)

        current_entry = modules_json["modules"].get(module)

        if current_entry is not None and self.sha is None:
            # Fetch the latest commit for the module
            current_version = current_entry["git_sha"]
            git_log = get_module_git_log(module, per_page=1, page_nbr=1)
            if len(git_log) == 0:
                log.error(f"Was unable to fetch version of module '{module}'")
                return False
            latest_version = git_log[0]["git_sha"]
            if current_version == latest_version and not self.force:
                log.info("Already up to date")
                return True
            elif not self.force:
                log.error("Found newer version of module.")
                self.latest = self.force = questionary.confirm(
                    "Do you want install it? (--force --latest)", default=False
                ).unsafe_ask()
                if not self.latest:
                    return False
        else:
            latest_version = None

        # Check that we don't already have a folder for this module
        if not self.check_module_files_installed(module, module_dir):
            return False

        if self.sha:
            if not current_entry is None and not self.force:
                return False
            if self.download_module_file(module, self.sha, install_folder, module_dir):
                self.update_modules_json(modules_json, modules_json_path, module, self.sha)
                return True
            else:
                try:
                    version = prompt_module_version_sha(module, installed_sha=current_entry["git_sha"])
                except SystemError as e:
                    log.error(e)
                    return False
        else:
            if self.latest:
                # Fetch the latest commit for the module
                if latest_version is None:
                    git_log = get_module_git_log(module, per_page=1, page_nbr=1)
                    if len(git_log) == 0:
                        log.error(f"Was unable to fetch version of module '{module}'")
                        return False
                    latest_version = git_log[0]["git_sha"]
                version = latest_version
            else:
                try:
                    version = prompt_module_version_sha(
                        module, installed_sha=current_entry["git_sha"] if not current_entry is None else None
                    )
                except SystemError as e:
                    log.error(e)
                    return False

        log.info("Installing {}".format(module))
        log.debug("Installing module '{}' at modules hash {}".format(module, self.modules_repo.modules_current_hash))

        # Download module files
        if not self.download_module_file(module, version, install_folder, module_dir):
            return False

        # Update module.json with newly installed module
        self.update_modules_json(modules_json, modules_json_path, module, version)
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
        return self.clear_module_dir(module_name=module, module_dir=module_dir)

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

    def clear_module_dir(self, module_name, module_dir):
        try:
            shutil.rmtree(module_dir)
            # Try cleaning up empty parent if tool/subtool and tool/ is empty
            if module_name.count("/") > 0:
                parent_dir = os.path.dirname(module_dir)
                try:
                    os.rmdir(parent_dir)
                except OSError:
                    log.debug(f"Parent directory not empty: '{parent_dir}'")
                else:
                    log.debug(f"Deleted orphan tool directory: '{parent_dir}'")
            log.debug("Successfully removed {} module".format(module_name))
            return True
        except OSError as e:
            log.error("Could not remove module: {}".format(e))
            return False

    def download_module_file(self, module_name, module_version, install_folder, module_dir):
        """Downloads the files of a module from the remote repo"""
        files = self.modules_repo.get_module_file_urls(module_name, module_version)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            split_filename = filename.split("/")
            dl_filename = os.path.join(self.pipeline_dir, "modules", *install_folder, *split_filename[1:])
            try:
                self.modules_repo.download_gh_file(dl_filename, api_url)
            except SystemError as e:
                log.error(e)
                return False
        log.info("Downloaded {} files to {}".format(len(files), module_dir))
        return True

    def check_module_files_installed(self, module_name, module_dir):
        """Checks if a module is already installed"""
        if os.path.exists(module_dir):
            if not self.force:
                log.error(f"Module directory '{module_dir}' already exists.")
                self.force = questionary.confirm(
                    "Do you want to overwrite local files? (--force)", default=False
                ).unsafe_ask()
            if self.force:
                log.info(f"Removing old version of module '{module_name}'")
                return self.clear_module_dir(module_name, module_dir)
            else:
                return False
        else:
            return True

    def update_modules_json(self, modules_json, modules_json_path, module_name, module_version):
        """Updates the 'module.json' file with new module info"""
        modules_json["modules"][module_name] = {"git_sha": module_version}
        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=4)
