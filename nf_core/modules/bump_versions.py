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
    ):
        self.dir = dir

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
                "Bumping nf-core modules versions", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
            )
            for mod in nfcore_modules:
                progress_bar.update(bump_progress, advance=1, test_name=mod.module_name)
                self.bump_module_version(mod)

    def bump_module_version(self, module: NFCoreModule):
        """
        Bump the bioconda and container version of a single NFCoreModule

        Args:
            module: NFCoreModule
        """

        # Get the current bioconda version

        # Check if a new version is available

        # Install the new version

        # Be done with it

        bioconda_packages = self.get_bioconda_version(module)

        # If multiple versions - don't update! (can't update mulled containers)
        if not bioconda_packages or len(bioconda_packages) > 1:
            return

        # Check for correct version and newer versions
        bioconda_tool_name = bioconda_packages[0].split("=")[0].replace("bioconda::", "").strip("'").strip('"')
        bp = bioconda_packages[0]
        bp = bp.strip("'").strip('"')
        try:
            bioconda_version = bp.split("=")[1]
            response = nf_core.utils.anaconda_package(bp)
        except LookupError as e:
            log.warn(f"Conda version not specified correctly: {module.main_nf}")
        except ValueError as e:
            log.warn(f"Conda version not specified correctly: {module.main_nf}")
        else:
            # Check that required version is available at all
            if bioconda_version not in response.get("versions"):
                log.error(f"Conda package had unknown version: `{module.main_nf}`")
                return  # No need to test for latest version, continue linting
            # Check version is latest available
            last_ver = response.get("latest_version")
            if last_ver is not None and last_ver != bioconda_version:
                package, ver = bp.split("=", 1)

                # Get docker and singularity container links
                try:
                    docker_img, singularity_img = nf_core.utils.get_biocontainer_tag(bioconda_tool_name, last_ver)
                except LookupError as e:
                    log.error(f"Could not update version for {bioconda_tool_name}: {e}")
                    return

                patterns = [
                    (bioconda_packages[0], f"bioconda::{bioconda_tool_name}={last_ver}"),
                    (r"quay.io/biocontainers/{}:.*".format(bioconda_tool_name), docker_img),
                    (r"https://depot.galaxyproject.org/singularity/{}:.*".format(bioconda_tool_name), singularity_img),
                ]

                with open(module.main_nf, "r") as fh:
                    content = fh.read()

                # Go over file content of main.nf and find replacements
                replacements = []
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

                            # Save for logging
                            replacements.append((line, newline))

                        # No match, keep line as it is
                        else:
                            newcontent.append(line)

                    if found_match:
                        content = "\n".join(newcontent)
                    else:
                        log.error(f"Could not update pattern in {module.main_nf}: '{pattern}'")

                # Write new content to the file
                with open(module.main_nf, "w") as fh:
                    fh.write(content)

            else:
                print("version up to date")
                return

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
            sys.exit(1)

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
