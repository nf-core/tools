"""
Bump versions for all modules on nf-core/modules
or for a single module
"""


from __future__ import print_function
import logging
import operator
import os
import questionary
import re
import requests
import rich
import yaml
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
import rich
from nf_core.utils import rich_force_colors
from nf_core.lint.pipeline_todos import pipeline_todos
import sys

import nf_core.utils
import nf_core.modules.module_utils
from nf_core.modules.pipeline_modules import ModulesRepo
from nf_core.modules.nfcore_module import NFCoreModule

log = logging.getLogger(__name__)


class ModuleVersionBumper(object):
    def __init__(
        self,
        dir=".",
        tool="",
    ):
        self.dir = dir
        self.tool = tool

    def bump_versions(self, module=None, all_modules=False):
        """
        Bump the container and conda version of single module or all modules

        Args:
            module: a specific module to update
            all_modules: whether to bump versions for all modules
        """

        # Verify that this is not a pipeline
        repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
        if not repo_type == "modules":
            log.error("This command only works on the nf-core/modules repository, not on pipelines!")
            sys.exit()

        # Get list of all modules
        _, nfcore_modules = nf_core.modules.module_utils.get_installed_modules(self.dir)

        # Prompt for module or all
        if module is None and not all_modules:
            question = {
                "type": "list",
                "name": "all_modules",
                "message": "Bump versions for all modules or a single named module?",
                "choices": ["All modules", "Named module"],
            }
            answer = questionary.unsafe_prompt([question], style=nf_core.utils.nfcore_question_style)
            if answer["all_modules"] == "All modules":
                all_modules = True
            else:
                module = questionary.autocomplete(
                    "Tool name:",
                    choices=[m.module_name for m in nfcore_modules],
                    style=nf_core.utils.nfcore_question_style,
                ).ask()

                # Only lint the given module
        if module:
            if all_modules:
                raise nf_core.modules.module_utils.ModuleException(
                    "You cannot specify a tool and request all tools to be bumped."
                )
            nfcore_modules = [m for m in nfcore_modules if m.module_name == module]
            if len(nfcore_modules) == 0:
                raise nf_core.modules.module_utils.ModuleException(f"Could not find the specified module: '{module}'")

        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            bump_progress = progress_bar.add_task(
                "Linting nf-core modules", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
            )
            for mod in nfcore_modules:
                progress_bar.update(bump_progress, advance=1, test_name=mod.module_name)
                self.bump_module_version(mod)

    def bump_module_version(module: NFCoreModule):
        """
        Bump the bioconda and container version of a single NFCoreModule

        Args:
            module: NFCoreModule
        """
        print("bumping that module")