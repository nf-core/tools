#!/usr/bin/env python
"""
The ModuleUpdate class handles generating of module templates
"""

from __future__ import print_function
import logging
import json
import os
import requests
import questionary
import rich
from rich.console import Console
from rich.table import Table
import rich
from nf_core.utils import rich_force_colors
from nf_core.lint.pipeline_todos import pipeline_todos
import sys

import nf_core.utils
from .pipeline_modules import ModulesRepo
from .lint import NFCoreModule
from .module_utils import get_module_commit_sha


log = logging.getLogger(__name__)


class ModuleUpdateException(Exception):
    """Exception raised when there was an error while updating a module"""

    pass


class ModuleUpdate(object):
    def __init__(self, dir):
        self.dir = dir
        self.modules_repo = ModulesRepo()
        self.modules_json = None
        self.updated = []
        self.up_to_date = []
        self.all_modules = False

    def update(self, module=None, all_modules=False):
        """
        Compares a module to the remote copy in the nf-core/modules repository
        and checks whether it is up to date
        If not, updated the module with the remote files

        Args:
            module: If not None, will update only this module
            all_modules: if True, all modules will be updated
        """

        # Get a list of all installed nf-core modules
        nfcore_modules = self.get_installed_modules()

        # Load the modules.json file
        try:
            with open(os.path.join(self.dir, "modules.json"), "r") as fh:
                self.modules_json = json.load(fh)
        except FileNotFoundError:
            log.error("Could not load 'modules.json' file!")
            sys.exit(1)

        # Prompt for module or all
        if module is None and not all_modules:
            question = {
                "type": "list",
                "name": "all_modules",
                "message": "Update all modules or a single named module?",
                "choices": ["All modules", "Named module"],
            }
            answer = questionary.unsafe_prompt([question], style=nf_core.utils.nfcore_question_style)
            if answer["all_modules"] == "All modules":
                self.all_modules = True
            else:
                module = questionary.autocomplete(
                    "Tool name:",
                    choices=[m.module_name for m in nfcore_modules],
                    style=nf_core.utils.nfcore_question_style,
                ).ask()

        # Only update the given module
        if module:
            if self.all_modules:
                raise ModuleUpdateException("You cannot specify a tool and request all tools to be updated.")
            nfcore_modules = [m for m in nfcore_modules if m.module_name == module]
            if len(nfcore_modules) == 0:
                raise ModuleUpdateException(f"Could not find the specified module: '{module}'")

        # Update all modules
        if len(nfcore_modules) > 0:
            progress_bar = rich.progress.Progress(
                "[bold blue]{task.description}",
                rich.progress.BarColumn(bar_width=None),
                "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
                transient=True,
            )
        with progress_bar:
            update_progress = progress_bar.add_task(
                "Updating nf-core modules", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
            )
            for mod in nfcore_modules:
                progress_bar.update(update_progress, advance=1, test_name=mod.module_name)
                if self.update_module(mod):
                    self.updated.append(mod)
                else:
                    self.up_to_date.append(mod)

        # Print the results
        self._print_results()

    def update_module(self, mod):
        """
        Update a single module
        """
        # Compare content to remote
        files_to_check = ["main.nf", "functions.nf", "meta.yml"]
        files_up_to_date = [False, False, False]
        remote_copies = [None, None, None]

        module_base_url = f"https://raw.githubusercontent.com/{self.modules_repo.name}/{self.modules_repo.branch}/software/{mod.module_name}/"
        for i, file in enumerate(files_to_check):
            try:
                local_copy = open(os.path.join(mod.module_dir, file), "r").read()
            except FileNotFoundError as e:
                log.debug(f"Could not open file: {os.path.join(mod.module_dir, file)}")
                continue

            # Download remote copy and compare
            url = module_base_url + file
            r = requests.get(url=url)

            if r.status_code != 200:
                log.error(f"Could not download remote copy of module {mod.module_name}")

            else:
                try:
                    remote_copy = r.content.decode("utf-8")
                    remote_copies[i] = remote_copy
                    if local_copy == remote_copy:
                        files_up_to_date[i] = True

                except UnicodeDecodeError as e:
                    log.error(f"Could not decode remote copy of {file} for the {mod.module_name} module")

        # All files are up to date
        if all(files_up_to_date):
            return False
        # Overwrite outdated files with remote copies and update the modules.json file
        else:
            for i, file in enumerate(files_to_check):
                # Only overwrite if remote copy could be fetched
                if remote_copies[i]:
                    local_file_path = os.path.join(mod.module_dir, file)
                    try:
                        with open(local_file_path, "w") as fh:
                            fh.write(remote_copies[i])
                    except Exception as e:
                        log.error(f"Could not update {file} of module '{mod.module_name}'")
                        sys.exit(1)

            # Update git_sha entries in modules.json
            module_git_sha = get_module_commit_sha(mod.module_name)
            self.modules_json["modules"][mod.module_name] = {"git_sha": module_git_sha}

            with open(os.path.join(self.dir, "modules.json"), "w") as fh:
                json.dump(self.modules_json, fh, indent=4)
            return True

    def get_installed_modules(self):
        """
        Make a list of all modules installed in this repository

        Returns a list for all nf-core modules, ignores local modules
        Nf-core module are returned as file paths to the module directories.
        In case the module contains several tools, one path to each tool directory
        is returned.

        returns nfcore_modules
        """
        # initialize lists
        nfcore_modules = []
        nfcore_modules_dir = os.path.join(self.dir, "modules", "nf-core", "software")

        # Get nf-core modules
        if os.path.exists(nfcore_modules_dir):
            for m in sorted([m for m in os.listdir(nfcore_modules_dir) if not m == "lib"]):
                if not os.path.isdir(os.path.join(nfcore_modules_dir, m)):
                    raise ModuleUpdateException(
                        f"File found in '{nfcore_modules_dir}': '{m}'! This directory should only contain module directories."
                    )
                m_content = os.listdir(os.path.join(nfcore_modules_dir, m))
                # Not a module, but contains sub-modules
                if not "main.nf" in m_content:
                    for tool in m_content:
                        nfcore_modules.append(os.path.join(m, tool))
                else:
                    nfcore_modules.append(m)

        # Make full (relative) file paths and create NFCoreModule objects
        nfcore_modules = [
            NFCoreModule(os.path.join(nfcore_modules_dir, m), repo_type="pipeline", base_dir=self.dir)
            for m in nfcore_modules
        ]

        return nfcore_modules

    def _print_results(self):
        """Print information about module updates

        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing final results")
        console = Console(force_terminal=rich_force_colors())

        if self.all_modules:
            # print summary table for all modules
            table = Table(box=rich.box.ROUNDED)
            table.add_column("[bold green]MODULE UPDATE SUMMARY".format(len(self.updated)), no_wrap=True)
            table.add_row(f"{len(self.up_to_date)} modules up to date", style="green")
            table.add_row(f"{len(self.updated)} outdated modules have been updated", style="yellow")
            if len(self.updated) > 0:
                for mod in self.updated:
                    table.add_row(f"[✔] {mod.module_name}", style="yellow")
            console.print(table)
        else:
            if len(self.updated) > 0:
                log.info(f"Updated module: {self.updated[0].module_name}")
            if len(self.up_to_date) > 0:
                log.info(f"The {self.up_to_date[0].module_name} module is up to date!")
