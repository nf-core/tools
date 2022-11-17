import logging
from pathlib import Path

import questionary
from rich.console import Console
from rich.rule import Rule
from rich.syntax import Syntax

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

        Args:
            component (str): Name of the component to remove

        Returns:
            bool: True if any item has been removed, False if not
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
        component_dir = Path(self.dir, self.component_type, repo_path, component)

        # Load the modules.json file
        modules_json = ModulesJson(self.dir)
        modules_json.load()

        # Verify that the module/subworkflow is actually installed
        if not component_dir.exists():
            log.error(f"Module directory does not exist: '{component_dir}'")

            if modules_json.module_present(component, self.modules_repo.remote_url, repo_path):
                log.error(f"Found entry for '{component}' in 'modules.json'. Removing...")
                modules_json.remove_entry(self.component_type, component, self.modules_repo.remote_url, repo_path)
            return False

        removed_by = None
        dependent_components = {component: self.component_type}
        if self.component_type == "subworkflows":
            removed_by = component
            dependent_components.update(
                modules_json.get_dependent_components(
                    self.component_type, component, self.modules_repo.remote_url, repo_path, dependent_components
                )
            )
        # remove all dependent components based on installed_by entry
        # Remove entry from modules.json
        removed = False
        removed_components = []
        for component_name, component_type in dependent_components.items():
            removed_component = modules_json.remove_entry(
                component_type,
                component_name,
                self.modules_repo.remote_url,
                repo_path,
                removed_by=removed_by,
            )
            removed_component_dir = Path(component_type, repo_path, component_name)
            if removed_component:
                if self.component_type == "subworkflows" and component_name != component:
                    # check if one of the dependent module/subworkflow has been manually included in the pipeline
                    include_stmts = self.check_if_in_include_stmts(str(removed_component_dir))
                    if include_stmts:
                        # print the include statements
                        log.warn(
                            f"The {component_type[:-1]} '{component_name}' is still included in the following workflow file{nf_core.utils.plural_s(include_stmts)}:"
                        )
                        console = Console()
                        for file, stmts in include_stmts.items():
                            console.print(Rule(f"{file}", style="white"))
                            for stmt in stmts:
                                console.print(
                                    Syntax(
                                        stmt["line"],
                                        "groovy",
                                        theme="ansi_dark",
                                        line_numbers=True,
                                        start_line=stmt["line_number"],
                                        padding=(0, 0, 1, 1),
                                    )
                                )

                # Remove the component files of all entries removed from modules.json
                removed_components.append(component_name.replace("/", "_"))
                removed = (
                    True
                    if self.clear_component_dir(component, Path(self.dir, removed_component_dir)) or removed
                    else False
                )
        if removed_components:
            log.info(f"Removed files for {', '.join(removed_components)}")
        return removed
