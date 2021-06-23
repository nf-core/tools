import json
from os import pipe
import rich
import logging

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
        if self.pipeline_dir is None:
            log.info(f"Modules available from {self.modules_repo.name} ({self.modules_repo.branch}):\n")

            # Get the list of available modules
            self.modules_repo.get_modules_file_tree()
            modules = self.modules_repo.modules_avail_module_names
            # Nothing found
            if len(modules) == 0:
                log.info(f"No available modules found in {self.modules_repo.name} ({self.modules_repo.branch})")
                return ""

        # We have a pipeline - list what's installed
        else:
            log.info(f"Modules installed in '{self.pipeline_dir}':\n")

            # Check whether pipelines is valid
            try:
                self.has_valid_pipeline()
            except UserWarning as e:
                log.error(e)
                return ""
            # Get installed modules
            self.get_pipeline_modules()
            modules = self.pipeline_module_names
            # Nothing found
            if len(modules) == 0:
                log.info(f"No nf-core modules found in '{self.pipeline_dir}'")
                return ""

        for mod in sorted(modules):
            table.add_row(mod)
        if print_json:
            return json.dumps(modules, sort_keys=True, indent=4)
        return table
