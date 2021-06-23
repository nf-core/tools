import os
import questionary
import logging

import nf_core.utils

from .modules_command import ModuleCommand

log = logging.getLogger(__name__)


class ModuleRemove(ModuleCommand):
    def __init__(self, pipeline_dir, module):
        """
        Initialise the ModulesRemove object and run remove command
        """
        super().__init__(pipeline_dir)
        self.module = module

    def remove(self):
        """
        Remove an already installed module
        This command only works for modules that are installed from 'nf-core/modules'
        """

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the installed modules
        self.get_pipeline_modules()

        if self.module is None:
            if len(self.pipeline_module_names) == 0:
                log.error("No installed modules found in pipeline")
                return False
            self.module = questionary.autocomplete(
                "Tool name:", choices=self.pipeline_module_names, style=nf_core.utils.nfcore_question_style
            ).ask()

        # Set the install folder based on the repository name
        install_folder = ["nf-core", "software"]
        if not self.modules_repo.name == "nf-core/modules":
            install_folder = ["external"]

        # Get the module directory
        module_dir = os.path.join(self.pipeline_dir, "modules", *install_folder, self.module)

        # Verify that the module is actually installed
        if not os.path.exists(module_dir):
            log.error("Module directory is not installed: {}".format(module_dir))
            log.info("The module you want to remove does not seem to be installed")
            return False

        log.info("Removing {}".format(self.module))

        # Remove the module
        return self.clear_module_dir(module_name=self.module, module_dir=module_dir)
