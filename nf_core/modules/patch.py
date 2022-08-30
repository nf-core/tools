import logging
import os
import shutil
import tempfile
from pathlib import Path

import questionary

import nf_core.utils

from .modules_command import ModuleCommand
from .modules_differ import ModulesDiffer
from .modules_json import ModulesJson

log = logging.getLogger(__name__)


class ModulePatch(ModuleCommand):
    def __init__(self, dir, remote_url=None, branch=None, no_pull=False):
        super().__init__(dir, remote_url, branch, no_pull)

        self.modules_json = ModulesJson(dir)

    def param_check(self, module):
        if not self.has_valid_directory():
            raise UserWarning()

        if module is not None and module not in self.modules_json.get_all_modules().get(self.modules_repo.fullname, {}):
            raise UserWarning(f"Module '{Path(self.modules_repo.fullname, module)}' does not exist in the pipeline")

    def patch(self, module=None):
        self.modules_json.check_up_to_date()
        self.param_check(module)

        if module is None:
            module = questionary.autocomplete(
                "Tool:",
                self.modules_json.get_all_modules()[self.modules_repo.fullname],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
        module_fullname = str(Path(self.modules_repo.fullname, module))

        # Verify that the module has an entry is the modules.json file
        if not self.modules_json.module_present(module, self.modules_repo.fullname):
            raise UserWarning(
                f"The '{module_fullname}' module does not have an entry in the 'modules.json' file. Cannot compute patch"
            )

        module_version = self.modules_json.get_module_version(module, self.modules_repo.fullname)
        if module_version is None:
            raise UserWarning(
                f"The '{module_fullname}' module does not have a valid version in the 'modules.json' file. Cannot compute patch"
            )
        # Get the module branch and reset it in the ModulesRepo object
        module_branch = self.modules_json.get_module_branch(module, self.modules_repo.fullname)
        if module_branch != self.modules_repo.branch:
            self.modules_repo.setup_branch(module_branch)

        # Set the diff filename based on the module name
        patch_filename = f"{module.replace('/', '-')}.diff"
        module_relpath = Path("modules", self.modules_repo.fullname, module)
        patch_relpath = Path(module_relpath, patch_filename)
        module_dir = Path(self.dir, module_relpath)
        patch_path = Path(self.dir, patch_relpath)

        if patch_path.exists():
            remove = questionary.confirm(
                f"Patch exists for module '{module_fullname}'. Do you want to regenerate it?",
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
            if remove:
                os.remove(patch_path)
            else:
                return

        # Create a temporary directory for storing the unchanged version of the module
        install_dir = tempfile.mkdtemp()
        module_install_dir = Path(install_dir, module)
        if not self.install_module_files(module, module_version, self.modules_repo, install_dir):
            raise UserWarning(
                f"Failed to install files of module '{module_fullname}' from remote ({self.modules_repo.remote_url})."
            )

        # Write the patch to a temporary location (otherwise it is printed to the screen later)
        patch_temp_path = tempfile.mktemp()
        try:
            ModulesDiffer.write_diff_file(
                patch_temp_path,
                module,
                self.modules_repo.fullname,
                module_install_dir,
                module_dir,
                for_git=False,
                dsp_from_dir=module_relpath,
                dsp_to_dir=module_relpath,
            )
        except UserWarning:
            raise UserWarning(f"Module '{module_fullname}' is unchanged. No patch to compute")

        # Write changes to modules.json
        self.modules_json.add_patch_entry(module, self.modules_repo.fullname, patch_relpath)

        # Show the changes made to the module
        ModulesDiffer.print_diff(
            module,
            self.modules_repo.fullname,
            module_install_dir,
            module_dir,
            dsp_from_dir=module_dir,
            dsp_to_dir=module_dir,
        )

        # Finally move the created patch file to its final location
        shutil.move(patch_temp_path, patch_path)
        log.info(f"Patch file of '{module_fullname}' written to '{patch_path}'")
