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
        if sum(map(len, self.module_names)) == 0:
            log.error("No installed modules found in pipeline")
            return False

        # Decide from which repo the module was installed
        # TODO Configure the prompt for repository name in a nice way
        if True:
            repo_name = self.modules_repo.name
        elif len(self.module_names) == 1:
            repo_name = list(self.module_names.keys())[0]
        else:
            repo_name = questionary.autocomplete(
                "Repo name:", choices=self.module_names.keys(), style=nf_core.utils.nfcore_question_style
            ).ask()

        if module is None:
            module = questionary.autocomplete(
                "Tool name:", choices=self.module_names[repo_name], style=nf_core.utils.nfcore_question_style
            ).ask()

        # Set the remove folder based on the repository name
        remove_folder = os.path.split(repo_name)

        # Get the module directory
        module_dir = os.path.join(self.dir, "modules", *remove_folder, module)

        # Verify that the module is actually installed
        if not os.path.exists(module_dir):
            log.error("Module directory is not installed: {}".format(module_dir))
            log.info("The module you want to remove does not seem to be installed")

            modules_json = self.load_modules_json()
            if self.modules_repo.name in modules_json["repos"] and module in modules_json["repos"][repo_name]:
                log.error(f"Found entry for '{module}' in 'modules.json'. Removing...")
                self.remove_modules_json_entry(module, repo_name, modules_json)
            return False

        log.info("Removing {}".format(module))

        # Remove entry from modules.json
        modules_json = self.load_modules_json()
        self.remove_modules_json_entry(module, repo_name, modules_json)

        # Remove the module
        return self.clear_module_dir(module_name=module, module_dir=module_dir)

    def remove_modules_json_entry(self, module, repo_name, modules_json):

        if not modules_json:
            return False
        if repo_name in modules_json.get("repos", {}):
            repo_entry = modules_json["repos"][repo_name]
            if module in repo_entry:
                repo_entry.pop(module)
            if len(repo_entry) == 0:
                modules_json["repos"].pop(repo_name)
        else:
            log.warning(f"Module '{repo_name}/{module}' is missing from 'modules.json' file.")
            return False

        self.dump_modules_json(modules_json)

        return True
