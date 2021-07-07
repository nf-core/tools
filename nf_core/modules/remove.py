import os
import sys
import json
import questionary
import logging


import nf_core.utils

from .modules_command import ModuleCommand

log = logging.getLogger(__name__)


class ModuleRemove(ModuleCommand):
    def __init__(self, pipeline_dir):
        """
        Initialise the ModulesRemove object and run remove command
        """
        super().__init__(pipeline_dir)

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

        if module is None:
            if len(self.module_names) == 0:
                log.error("No installed modules found in pipeline")
                return False
            module = questionary.autocomplete(
                "Tool name:", choices=self.module_names, style=nf_core.utils.nfcore_question_style
            ).ask()

        # Set the install folder based on the repository name
        install_folder = ["nf-core", "modules"]
        if not self.modules_repo.name == "nf-core/modules":
            install_folder = ["external"]

        # Get the module directory
        module_dir = os.path.join(self.dir, "modules", *install_folder, module)

        # Verify that the module is actually installed
        if not os.path.exists(module_dir):
            log.error("Module directory is not installed: {}".format(module_dir))
            log.info("The module you want to remove does not seem to be installed")
            modules_json = self.load_modules_json()
            if module in modules_json.get("modules"):
                log.error(f"Found entry for '{module}' in 'modules.json'. Removing...")
                modules_json["modules"].pop(module)
                self.dump_modules_json(modules_json)
            return False

        log.info("Removing {}".format(module))

        # Remove entry from modules.json
        self.remove_modules_json_entry(module)

        # Remove the module
        return self.clear_module_dir(module_name=module, module_dir=module_dir)

    def remove_modules_json_entry(self, module):
        # Load 'modules.json'
        modules_json = self.load_modules_json()
        if not modules_json:
            return False
        if module in modules_json.get("modules", {}):
            modules_json["modules"].pop(module)
        else:
            log.error(f"Module '{module}' is missing from 'modules.json' file.")
            return False

        self.dump_modules_json(modules_json)

        return True
