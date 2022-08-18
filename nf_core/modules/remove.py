import logging
from pathlib import Path

import questionary

import nf_core.utils

from .modules_command import ModuleCommand
from .modules_json import ModulesJson

log = logging.getLogger(__name__)


class ModuleRemove(ModuleCommand):
    def remove(self, module):
        """
        Remove an already installed module
        This command only works for modules that are installed from 'nf-core/modules'
        """
        if self.repo_type == "modules":
            log.error("You cannot remove a module in a clone of nf-core/modules")
            return False

        # Check whether pipeline is valid and with a modules.json file
        self.has_valid_directory()
        self.has_modules_file()

        repo_name = self.modules_repo.fullname
        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.modules_from_repo(repo_name),
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Get the module directory
        module_dir = Path(self.dir, "modules", repo_name, module)

        # Load the modules.json file
        modules_json = ModulesJson(self.dir)
        modules_json.load()

        # Verify that the module is actually installed
        if not module_dir.exists():
            log.error(f"Module directory does not exist: '{module_dir}'")

            if modules_json.module_present(module, repo_name):
                log.error(f"Found entry for '{module}' in 'modules.json'. Removing...")
                modules_json.remove_entry(module, repo_name)
            return False

        log.info(f"Removing {module}")

        # Remove entry from modules.json
        modules_json.remove_entry(module, repo_name)

        # Remove the module
        return self.clear_module_dir(module_name=module, module_dir=module_dir)
