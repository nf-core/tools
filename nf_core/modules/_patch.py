import tempfile
from pathlib import Path

import questionary

from .modules_command import ModuleCommand
from .modules_differ import ModulesDiffer
from .modules_json import ModulesJson


class ModulePatch(ModuleCommand):
    def __init__(self, dir, remote_url=None, branch=None, no_pull=False, base_path=None):
        super().__init__(dir, remote_url, branch, no_pull, base_path)

        self.modules_json = ModulesJson(dir)
        self.get_pipeline_modules()

    def param_check(self, module):
        if not self.has_valid_directory():
            raise UserWarning()

        if module is not None and module not in self.module_names[self.modules_repo.fullname]:
            raise UserWarning(f"Module '{module}' does not exist in the pipeline")

    def patch(self, module=None):
        self.param_check(module)

        if module is None:
            module = questionary.autocomplete("Tool", self.module_names[self.modules_repo.fullname]).unsafe_ask()

        # Verify that the module has an entry is the modules.json file
        if not self.modules_json.module_present(module, self.modules_repo.fullname):
            raise UserWarning(
                f"The '{module}' module does not have an entry in the 'modules.json' file. Cannot compute patch"
            )

        module_version = self.modules_json.get_module_version(module, self.modules_repo.fullname)
        if module_version is None:
            raise UserWarning(
                f"The '{module}' does not have a valid version in the 'modules.json' file. Cannot compute patch"
            )

        # Create a temporary directory for storing the unchanged version of the module
        install_dir = tempfile.mkdtemp()
        if not self.install_module_files(module, module_version, self.modules_repo, install_dir):
            raise UserWarning(
                f"Failed to install files of module '{module}' from remote ({self.modules_repo.remote_url})."
            )

        # Set the diff filename based on the module name
        patch_filename = f"{'-'.join(module.split())}.diff"
        module_dir = Path(self.dir, "modules", self.modules_repo.fullname, module)
        patch_relpath = Path(module_dir, patch_filename)
        patch_path = Path(self.dir, patch_relpath)

        ModulesDiffer.write_diff_file(patch_path, module, module_dir, install_dir, None, None)

        # Write changes to modules.json
        self.modules_json.add_patch_entry(module, self.modules_repo.fullname, patch_relpath)
