import json
import logging
import os
import sys

import questionary

import nf_core.utils

from .modules_command import ModuleCommand
from .modules_json import ModulesJson

log = logging.getLogger(__name__)


class ModuleRemove(ModuleCommand):
    def __init__(self, pipeline_dir, remote_url=None, branch=None, no_pull=False, base_path=None):
        """
        Initialise the ModulesRemove object and run remove command
        """
        super().__init__(pipeline_dir, remote_url, branch, no_pull, base_path)

    def remove(self, module):
        """
        Remove an already installed module
        This command only works for modules that are installed from 'nf-core/modules'
        """
        if self.repo_type == "modules":
            log.error("You cannot remove a module in a clone of nf-core/modules")
            return False

        # Check whether pipelines is valid
        self.has_valid_directory()

        # Get the installed modules
        self.get_pipeline_modules()
        if sum(map(len, self.module_names)) == 0:
            log.error("No installed modules found in pipeline")
            return False

        # Decide from which repo the module was installed
        # TODO Configure the prompt for repository name in a nice way
        if True:
            repo_name = self.modules_repo.fullname
        elif len(self.module_names) == 1:
            repo_name = list(self.module_names.keys())[0]
        else:
            repo_name = questionary.autocomplete(
                "Repo name:", choices=self.module_names.keys(), style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()

        if module is None:
            module = questionary.autocomplete(
                "Tool name:", choices=self.module_names[repo_name], style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()

        # Set the remove folder based on the repository name
        remove_folder = os.path.split(repo_name)

        # Get the module directory
        module_dir = os.path.join(self.dir, "modules", *remove_folder, module)

        # Load the modules.json file
        modules_json = ModulesJson(self.dir)
        modules_json.load_modules_json()

        # Verify that the module is actually installed
        if not os.path.exists(module_dir):
            log.error(f"Module directory does not exist: '{module_dir}'")

            if modules_json.module_present(module, repo_name):
                log.error(f"Found entry for '{module}' in 'modules.json'. Removing...")
                modules_json.remove_modules_json_entry(module, repo_name)
            return False

        log.info(f"Removing {module}")

        # Remove entry from modules.json
        modules_json.remove_modules_json_entry(module, repo_name)

        # Remove the module
        return self.clear_module_dir(module_name=module, module_dir=module_dir)
