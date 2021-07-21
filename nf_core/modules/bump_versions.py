"""
Bump versions for all modules on nf-core/modules
or for a single module
"""


from __future__ import print_function
import logging
import questionary
import os
import re
import rich
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
import rich
from nf_core.utils import rich_force_colors
import sys
import yaml

import nf_core.utils
import nf_core.modules.module_utils
from nf_core.modules.nfcore_module import NFCoreModule
from .modules_command import ModuleCommand

log = logging.getLogger(__name__)


class ModuleVersionBumper(ModuleCommand):
    def __init__(self, pipeline_dir):
        super().__init__(pipeline_dir)

        self.up_to_date = None
        self.updated = None
        self.failed = None
        self.show_up_to_date = None
        self.tools_config = {}

    def bump_versions(self, module=None, all_modules=False, show_uptodate=False):
        """
        Bump the container and conda version of single module or all modules

        Looks for a bioconda tool version in the `main.nf` file of the module and checks whether
        are more recent version is available. If yes, then tries to get docker/singularity
        container links and replace the bioconda version and the container links in the main.nf file
        of the respective module.

        Args:
            module: a specific module to update
            all_modules: whether to bump versions for all modules
        """
        self.up_to_date = []
        self.updated = []
        self.failed = []
        self.show_up_to_date = show_uptodate

        # Verify that this is not a pipeline
        repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
        if not repo_type == "modules":
            raise nf_core.modules.module_utils.ModuleException(
                "This command only works on the nf-core/modules repository, not on pipelines!"
            )

        # Get list of all modules
        _, nfcore_modules = nf_core.modules.module_utils.get_installed_modules(self.dir)

        # Load the .nf-core-tools.config
        self.tools_config = nf_core.utils.load_tools_config(self.dir)

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

        if module:
            self.show_up_to_date = True
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
                "Bumping nf-core modules versions", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
            )
            for mod in nfcore_modules:
                progress_bar.update(bump_progress, advance=1, test_name=mod.module_name)
                self.bump_module_version(mod)

        self._print_results()

    def bump_module_version(self, module: NFCoreModule):
        """
        Bump the bioconda and container version of a single NFCoreModule

        Args:
            module: NFCoreModule
        """
        config_version = None
        # Extract bioconda version from `main.nf`
        bioconda_packages = self.get_bioconda_version(module)

        # If multiple versions - don't update! (can't update mulled containers)
        if not bioconda_packages or len(bioconda_packages) > 1:
            self.failed.append((f"Ignoring mulled container", module.module_name))
            return False

        # Don't update if blocked in blacklist
        self.bump_versions_config = self.tools_config.get("bump-versions", {})
        if module.module_name in self.bump_versions_config:
            config_version = self.bump_versions_config[module.module_name]
            if not config_version:
                self.up_to_date.append((f"Omitting module due to config: {module.module_name}", module.module_name))
                return False

        # check for correct version and newer versions
        bioconda_tool_name = bioconda_packages[0].split("=")[0].replace("bioconda::", "").strip("'").strip('"')
        bp = bioconda_packages[0]
        bp = bp.strip("'").strip('"')
        bioconda_version = bp.split("=")[1]

        if not config_version:
            try:
                response = nf_core.utils.anaconda_package(bp)
            except (LookupError, ValueError) as e:
                self.failed.append((f"Conda version not specified correctly: {module.main_nf}", module.module_name))
                return False

            # Check that required version is available at all
            if bioconda_version not in response.get("versions"):
                self.failed.append((f"Conda package had unknown version: `{module.main_nf}`", module.module_name))
                return False

            # Check version is latest available
            last_ver = response.get("latest_version")
        else:
            last_ver = config_version

        if last_ver is not None and last_ver != bioconda_version:
            log.debug(f"Updating version for {module.module_name}")
            # Get docker and singularity container links
            try:
                docker_img, singularity_img = nf_core.utils.get_biocontainer_tag(bioconda_tool_name, last_ver)
            except LookupError as e:
                self.failed.append((f"Could not download container tags: {e}", module.module_name))
                return False

            patterns = [
                (bioconda_packages[0], f"'bioconda::{bioconda_tool_name}={last_ver}'"),
                (r"quay.io/biocontainers/{}:[^'\"\s]+".format(bioconda_tool_name), docker_img),
                (
                    r"https://depot.galaxyproject.org/singularity/{}:[^'\"\s]+".format(bioconda_tool_name),
                    singularity_img,
                ),
            ]

            with open(module.main_nf, "r") as fh:
                content = fh.read()

            # Go over file content of main.nf and find replacements
            for pattern in patterns:
                found_match = False
                newcontent = []
                for line in content.splitlines():

                    # Match the pattern
                    matches_pattern = re.findall("^.*{}.*$".format(pattern[0]), line)
                    if matches_pattern:
                        found_match = True

                        # Replace the match
                        newline = re.sub(pattern[0], pattern[1], line)
                        newcontent.append(newline)
                    # No match, keep line as it is
                    else:
                        newcontent.append(line)

                if found_match:
                    content = "\n".join(newcontent)
                else:
                    self.failed.append(
                        (f"Did not find pattern {pattern[0]} in module {module.module_name}", module.module_name)
                    )
                    return False

            # Write new content to the file
            with open(module.main_nf, "w") as fh:
                fh.write(content)

            self.updated.append(
                (
                    f"Module updated:  {bioconda_version} --> {last_ver}",
                    module.module_name,
                )
            )
            return True

        else:
            self.up_to_date.append((f"Module version up to date: {module.module_name}", module.module_name))
            return True

    def get_bioconda_version(self, module):
        """
        Extract the bioconda version from a module
        """
        # Check whether file exists and load it
        bioconda_packages = None
        try:
            with open(module.main_nf, "r") as fh:
                lines = fh.readlines()
        except FileNotFoundError as e:
            log.error(f"Could not read `main.nf` of {module.module_name} module.")
            return False

        for l in lines:
            if re.search("bioconda::", l):
                bioconda_packages = [b for b in l.split() if "bioconda::" in b]
            if re.search("org/singularity", l):
                singularity_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()
            if re.search("biocontainers", l):
                docker_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()

        if bioconda_packages:
            return bioconda_packages
        else:
            return False

    def _print_results(self):
        """
        Print the results for the bump_versions command
        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing bump_versions results")

        console = Console(force_terminal=rich_force_colors())
        # Find maximum module name length
        max_mod_name_len = 40
        for m in [self.up_to_date, self.updated, self.failed]:
            try:
                max_mod_name_len = max(len(m[2]), max_mod_name_len)
            except:
                pass

        def _s(some_list):
            if len(some_list) > 1:
                return "s"
            return ""

        def format_result(module_updates, table):
            """
            Create rows for module updates
            """
            # TODO: Row styles don't work current as table-level style overrides.
            # I'd like to make an issue about this on the rich repo so leaving here in case there is a future fix
            last_modname = False
            row_style = None
            for module_update in module_updates:
                if last_modname and module_update[1] != last_modname:
                    if row_style:
                        row_style = None
                    else:
                        row_style = "magenta"
                last_modname = module_update[1]
                table.add_row(
                    Markdown(f"{module_update[1]}"),
                    Markdown(f"{module_update[0]}"),
                    style=row_style,
                )
            return table

        # Table of up to date modules
        if len(self.up_to_date) > 0 and self.show_up_to_date:
            console.print(
                rich.panel.Panel(
                    r"[!] {} Module{} version{} up to date.".format(
                        len(self.up_to_date), _s(self.up_to_date), _s(self.up_to_date)
                    ),
                    style="bold green",
                )
            )
            table = Table(style="green", box=rich.box.ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("Update Message")
            table = format_result(self.up_to_date, table)
            console.print(table)

        # Table of updated modules
        if len(self.updated) > 0:
            console.print(
                rich.panel.Panel(
                    r"[!] {} Module{} updated".format(len(self.updated), _s(self.updated)), style="bold yellow"
                )
            )
            table = Table(style="yellow", box=rich.box.ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("Update message")
            table = format_result(self.updated, table)
            console.print(table)

        # Table of modules that couldn't be updated
        if len(self.failed) > 0:
            console.print(
                rich.panel.Panel(
                    r"[!] {} Module update{} failed".format(len(self.failed), _s(self.failed)), style="bold red"
                )
            )
            table = Table(style="red", box=rich.box.ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("Update message")
            table = format_result(self.failed, table)
            console.print(table)
