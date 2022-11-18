import logging
from pathlib import Path

import questionary
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax

import nf_core.utils
from nf_core.components.components_command import ComponentCommand
from nf_core.modules.modules_json import ModulesJson

log = logging.getLogger(__name__)


class ComponentRemove(ComponentCommand):
    def __init__(self, component_type, pipeline_dir):
        super().__init__(component_type, pipeline_dir)

    def remove(self, component, force=False):
        """
        Remove an already installed module/subworkflow
        This command only works for modules/subworkflows that are installed from 'nf-core/modules'

        Args:
            component (str): Name of the component to remove
            force (bool): Force removal of component, even if there is still an include statement in a workflow file

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

        repo_path = self.modules_repo.repo_path
        if component is None:
            component = questionary.autocomplete(
                f"{self.component_type[:-1]} name:",
                choices=self.components_from_repo(repo_path),
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Get the module/subworkflow directory
        component_dir = Path(self.dir, self.component_type, repo_path, component)

        # Load the modules.json file
        modules_json = ModulesJson(self.dir)
        modules_json.load()

        # Verify that the module/subworkflow is actually installed
        if not component_dir.exists():
            log.error(f"Installation directory '{component_dir}' does not exist.")

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
            current_version = modules_json.get_component_version(
                component_type, component_name, self.modules_repo.remote_url, repo_path
            )
            removed_component = modules_json.remove_entry(
                component_type,
                component_name,
                self.modules_repo.remote_url,
                repo_path,
                removed_by=removed_by,
            )
            removed_component_dir = Path(component_type, repo_path, component_name)
            if removed_component:
                # check if one of the dependent module/subworkflow has been manually included in the pipeline
                include_stmts = self.check_if_in_include_stmts(str(removed_component_dir))
                if include_stmts:
                    # print the include statements
                    log.warn(
                        f"The {component_type[:-1]} '{component_name}' is still included in the following workflow file{nf_core.utils.plural_s(include_stmts)}:"
                    )
                    console = Console()
                    for file, stmts in include_stmts.items():
                        renderables = []
                        for stmt in stmts:
                            renderables.append(
                                Syntax(
                                    stmt["line"],
                                    "groovy",
                                    theme="ansi_dark",
                                    line_numbers=True,
                                    start_line=stmt["line_number"],
                                )
                            )
                        console.print(
                            Panel(
                                Group(*renderables),
                                title=f"{file}",
                                style="white",
                                title_align="center",
                                padding=1,
                            )
                        )
                    # ask the user if they still want to remove the component, add it back otherwise
                    if not force:
                        if not questionary.confirm(
                            f"Do you still want to remove the {component_type[:-1]} '{component_name}'?",
                            style=nf_core.utils.nfcore_question_style,
                        ).unsafe_ask():
                            # add the component back to modules.json
                            if not modules_json.update(
                                self.component_type,
                                self.modules_repo,
                                component_name,
                                current_version,
                                self.component_type,
                            ):
                                log.warn(
                                    f"Could not install the {component_type[:-1]} '{component_name}', please install it manually with 'nf-core {component_type} install  {component_name}'."
                                )
                            continue
                # Remove the component files of all entries removed from modules.json
                removed = (
                    True
                    if self.clear_component_dir(component, Path(self.dir, removed_component_dir)) or removed
                    else False
                )
                if removed:
                    # remember removed dependencies
                    if component_name != component:
                        removed_components.append(component_name.replace("/", "_"))
                    if removed_components:
                        log.info(
                            f"Removed files for '{component}' and it's dependencies '{', '.join(removed_components)}'."
                        )
                    else:
                        log.info(f"Removed files for '{component}'.")
        return removed
