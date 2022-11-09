import logging
from pathlib import Path

import questionary

import nf_core.utils
from nf_core.components.components_command import ComponentCommand
from nf_core.modules.modules_json import ModulesJson

log = logging.getLogger(__name__)


class ComponentRemove(ComponentCommand):
    def __init__(self, component_type, pipeline_dir):
        super().__init__(component_type, pipeline_dir)

    def remove(self, component):
        """
        Remove an already installed module/subworkflow
        This command only works for modules/subworkflows that are installed from 'nf-core/modules'
        """
        if self.repo_type == "modules":
            log.error(f"You cannot remove a {self.component_type[:-1]} in a clone of nf-core/modules")
            return False

        # Check modules directory structure
        self.check_modules_structure()

        # Check whether pipeline is valid and with a modules.json file
        self.has_valid_directory()
        self.has_modules_file()

        repo_dir = self.modules_repo.fullname
        repo_path = self.modules_repo.repo_path
        if component is None:
            component = questionary.autocomplete(
                f"{self.component_type[:-1]} name:",
                choices=self.components_from_repo(repo_dir),
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Get the module/subworkflow directory
        module_dir = Path(self.dir, self.component_type, repo_path, component)

        # Load the modules.json file
        modules_json = ModulesJson(self.dir)
        modules_json.load()

        # Verify that the module/subworkflow is actually installed
        if not module_dir.exists():
            log.error(f"Module directory does not exist: '{module_dir}'")

            if modules_json.module_present(component, self.modules_repo.remote_url, repo_path):
                log.error(f"Found entry for '{component}' in 'modules.json'. Removing...")
                modules_json.remove_entry(self.component_type, component, self.modules_repo.remote_url, repo_path)
            return False

        # Remove entry from modules.json
        removed_by = component if self.component_type == "subworkflows" else None
        removed = False
        removed = modules_json.remove_entry(
            self.component_type, component, self.modules_repo.remote_url, repo_path, removed_by=removed_by
        )
        # Remove the module files
        if removed:
            removed = self.clear_component_dir(component, module_dir)

        return removed
