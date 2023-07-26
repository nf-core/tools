import logging
import os
import shutil
import tempfile
from pathlib import Path

import questionary

import nf_core.utils
from nf_core.components.components_command import ComponentCommand

from .modules_differ import ModulesDiffer
from .modules_json import ModulesJson

log = logging.getLogger(__name__)


class ModulePatch(ComponentCommand):
    def __init__(self, dir, remote_url=None, branch=None, no_pull=False):
        super().__init__("modules", dir, remote_url, branch, no_pull)

        self.modules_json = ModulesJson(dir)

    def param_check(self, module):
        if not self.has_valid_directory():
            raise UserWarning()

        modules = self.modules_json.get_all_components(self.component_type)[self.modules_repo.remote_url]
        module_names = [module for _, module in modules]

        if module is not None and module not in module_names:
            module_dir = [dir for dir, m in modules if m == module][0]
            raise UserWarning(f"Module '{Path('modules', module_dir, module)}' does not exist in the pipeline")

    def patch(self, module=None):
        # Check modules directory structure
        self.check_modules_structure()

        self.modules_json.check_up_to_date()
        self.param_check(module)
        modules = self.modules_json.get_all_components(self.component_type)[self.modules_repo.remote_url]

        if module is None:
            choices = [
                module if directory == self.modules_repo.repo_path else f"{directory}/{module}"
                for directory, module in modules
            ]
            module = questionary.autocomplete(
                "Tool:",
                choices,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
        module_dir = [dir for dir, m in modules if m == module][0]
        module_fullname = str(Path("modules", module_dir, module))

        # Verify that the module has an entry in the modules.json file
        if not self.modules_json.module_present(module, self.modules_repo.remote_url, module_dir):
            raise UserWarning(
                f"The '{module_fullname}' module does not have an entry in the 'modules.json' file. Cannot compute patch"
            )

        module_version = self.modules_json.get_module_version(module, self.modules_repo.remote_url, module_dir)
        if module_version is None:
            raise UserWarning(
                f"The '{module_fullname}' module does not have a valid version in the 'modules.json' file. Cannot compute patch"
            )
        # Get the module branch and reset it in the ModulesRepo object
        module_branch = self.modules_json.get_component_branch(
            self.component_type, module, self.modules_repo.remote_url, module_dir
        )
        if module_branch != self.modules_repo.branch:
            self.modules_repo.setup_branch(module_branch)

        # Set the diff filename based on the module name
        patch_filename = f"{module.replace('/', '-')}.diff"
        module_relpath = Path("modules", module_dir, module)
        patch_relpath = Path(module_relpath, patch_filename)
        module_current_dir = Path(self.dir, module_relpath)
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
        if not self.install_component_files(module, module_version, self.modules_repo, install_dir):
            raise UserWarning(
                f"Failed to install files of module '{module}' from remote ({self.modules_repo.remote_url})."
            )

        # Write the patch to a temporary location (otherwise it is printed to the screen later)
        patch_temp_path = tempfile.mktemp()
        try:
            ModulesDiffer.write_diff_file(
                patch_temp_path,
                module,
                self.modules_repo.repo_path,
                module_install_dir,
                module_current_dir,
                for_git=False,
                dsp_from_dir=module_relpath,
                dsp_to_dir=module_relpath,
            )
            log.debug(f"Patch file wrote to a temporary directory {patch_temp_path}")
        except UserWarning:
            raise UserWarning(f"Module '{module_fullname}' is unchanged. No patch to compute")

        # Write changes to modules.json
        self.modules_json.add_patch_entry(module, self.modules_repo.remote_url, module_dir, patch_relpath)
        log.debug(f"Wrote patch path for module {module} to modules.json")

        # Show the changes made to the module
        ModulesDiffer.print_diff(
            module,
            self.modules_repo.repo_path,
            module_install_dir,
            module_current_dir,
            dsp_from_dir=module_current_dir,
            dsp_to_dir=module_current_dir,
        )

        # Finally move the created patch file to its final location
        shutil.move(patch_temp_path, patch_path)
        log.info(f"Patch file of '{module_fullname}' written to '{patch_path}'")

    def remove(self, module):
        # Check modules directory structure
        self.check_modules_structure()

        self.modules_json.check_up_to_date()
        self.param_check(module)
        modules = self.modules_json.get_all_components(self.component_type)[self.modules_repo.remote_url]

        if module is None:
            choices = [
                module if directory == self.modules_repo.repo_path else f"{directory}/{module}"
                for directory, module in modules
            ]
            module = questionary.autocomplete(
                "Tool:",
                choices,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
        module_dir = [dir for dir, m in modules if m == module][0]
        module_fullname = str(Path("modules", module_dir, module))

        # Verify that the module has an entry in the modules.json file
        if not self.modules_json.module_present(module, self.modules_repo.remote_url, module_dir):
            raise UserWarning(
                f"The '{module_fullname}' module does not have an entry in the 'modules.json' file. Cannot compute patch"
            )

        module_version = self.modules_json.get_module_version(module, self.modules_repo.remote_url, module_dir)
        if module_version is None:
            raise UserWarning(
                f"The '{module_fullname}' module does not have a valid version in the 'modules.json' file. Cannot compute patch"
            )
        # Get the module branch and reset it in the ModulesRepo object
        module_branch = self.modules_json.get_component_branch(
            self.component_type, module, self.modules_repo.remote_url, module_dir
        )
        if module_branch != self.modules_repo.branch:
            self.modules_repo.setup_branch(module_branch)

        # Set the diff filename based on the module name
        patch_filename = f"{module.replace('/', '-')}.diff"
        module_relpath = Path("modules", module_dir, module)
        patch_relpath = Path(module_relpath, patch_filename)
        patch_path = Path(self.dir, patch_relpath)
        module_path = Path(self.dir, module_relpath)

        if patch_path.exists():
            remove = questionary.confirm(
                f"Patch exists for module '{module_fullname}'. Are you sure you want to remove?",
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
            if not remove:
                return

        # Try to apply the patch in reverse and move resulting files to module dir
        temp_module_dir = self.modules_json.try_apply_patch_reverse(
            module, self.modules_repo.repo_path, patch_relpath, module_path
        )
        try:
            for file in Path(temp_module_dir).glob("*"):
                file.rename(module_path.joinpath(file.name))
            os.rmdir(temp_module_dir)
        except Exception as err:
            raise UserWarning(f"There was a problem reverting the patched file: {err}")

        log.info(f"Patch for {module} reverted!")
        # Remove patch file if we could revert the patch
        patch_path.unlink()
        # Write changes to module.json
        self.modules_json.remove_patch_entry(module, self.modules_repo.remote_url, module_dir)

        if not all(
            self.modules_repo.component_files_identical(module, module_path, module_version, "modules").values()
        ):
            log.error(
                f"Module files do not appear to match the remote for the commit sha in the 'module.json': {module_version}\n"
                f"Recommend reinstalling with 'nf-core modules install --force --sha {module_version} {module}' "
            )
