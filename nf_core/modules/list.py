import json
from os import pipe
import rich
import logging

import nf_core.modules.module_utils

from .modules_command import ModuleCommand

log = logging.getLogger(__name__)


class ModuleList(ModuleCommand):
    def __init__(self, pipeline_dir):
        super().__init__(pipeline_dir)

    def list_modules(self, print_json=False):
        """
        Get available module names from GitHub tree for repo
        and print as list to stdout
        """

        # Initialise rich table
        table = rich.table.Table()
        table.add_column("Module Name")
        modules = []

        # No pipeline given - show all remote
        if self.dir is None:
            log.info(f"Modules available from {self.modules_repo.name} ({self.modules_repo.branch}):\n")

            # Get the list of available modules
            try:
                self.modules_repo.get_modules_file_tree()
            except LookupError as e:
                log.error(e)
                return False

            modules = self.modules_repo.modules_avail_module_names
            # Nothing found
            if len(modules) == 0:
                log.info(f"No available modules found in {self.modules_repo.name} ({self.modules_repo.branch})")
                return ""
            for mod in sorted(modules):
                table.add_row(mod)

        # We have a pipeline - list what's installed
        else:
            log.info(f"Modules installed in '{self.dir}':\n")

            # Check whether pipelines is valid
            try:
                self.has_valid_directory()
            except UserWarning as e:
                log.error(e)
                return ""
            # Get installed modules
            self.get_pipeline_modules()
            modules = self.module_names
            # Nothing found
            if len(modules) == 0:
                log.info(f"No nf-core modules found in '{self.dir}'")
                return ""

            modules_json = self.load_modules_json()
            if not modules_json:
                # If the modules.json file is missing we show the old version
                # of the list command, i.e only names
                for mod in sorted(modules):
                    table.add_row(mod)
            else:
                table.add_column("Version SHA")
                table.add_column("Message")
                table.add_column("Date")

                for module in sorted(modules):
                    module_entry = modules_json["modules"].get(module)
                    if module_entry:
                        version_sha = module_entry["git_sha"]
                        try:
                            message, date = nf_core.modules.module_utils.get_commit_info(version_sha)
                        except LookupError as e:
                            log.warning(e)
                            date = "[red]Not Available"
                            message = "[red]Not Available"
                    else:
                        log.warning(f"Commit SHA for module {module} is missing from 'modules.json'")
                        version_sha = "[red]Not Available"
                        date = "[red]Not Available"
                        message = "[red]Not Available"
                    table.add_row(module, version_sha, message, date)

        if print_json:
            return json.dumps(modules, sort_keys=True, indent=4)
        return table
