import logging
import os

import nf_core.components.components_install
import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.components_command import ComponentCommand
from nf_core.modules.modules_json import ModulesJson

log = logging.getLogger(__name__)


class ModuleInstall(ComponentCommand):
    def __init__(
        self,
        pipeline_dir,
        force=False,
        prompt=False,
        sha=None,
        remote_url=None,
        branch=None,
        no_pull=False,
        installed_by=False,
    ):
        super().__init__("modules", pipeline_dir, remote_url, branch, no_pull)
        self.force = force
        self.prompt = prompt
        self.sha = sha
        if installed_by:
            self.installed_by = installed_by
        else:
            self.installed_by = self.component_type

    def install(self, module, silent=False):
        if self.repo_type == "modules":
            log.error("You cannot install a module in a clone of nf-core/modules")
            return False
        # Check whether pipelines is valid
        if not self.has_valid_directory():
            return False

        # Check modules directory structure
        self.check_modules_structure()

        # Verify that 'modules.json' is consistent with the installed modules
        modules_json = ModulesJson(self.dir)
        modules_json.check_up_to_date()

        # Verify SHA
        if not self.modules_repo.verify_sha(self.prompt, self.sha):
            return False

        # Check and verify module name
        module = nf_core.components.components_install.collect_and_verify_name(
            self.component_type, module, self.modules_repo
        )
        if not module:
            return False

        # Get current version
        current_version = modules_json.get_module_version(
            module, self.modules_repo.remote_url, self.modules_repo.repo_path
        )

        # Set the install folder based on the repository name
        install_folder = os.path.join(self.dir, "modules", self.modules_repo.repo_path)

        # Compute the module directory
        module_dir = os.path.join(install_folder, module)

        # Check that the module is not already installed
        if not nf_core.components.components_install.check_component_installed(
            self.component_type, module, current_version, module_dir, self.modules_repo, self.force, self.prompt
        ):
            log.debug(
                f"Module is already installed and force is not set.\nAdding the new installation source {self.installed_by} for module {module} to 'modules.json' without installing the module."
            )
            modules_json.load()
            modules_json.update(self.component_type, self.modules_repo, module, current_version, self.installed_by)
            return False

        version = nf_core.components.components_install.get_version(
            module, self.component_type, self.sha, self.prompt, current_version, self.modules_repo
        )
        if not version:
            return False

        # Remove module if force is set
        install_track = None
        if self.force:
            log.info(f"Removing installed version of '{self.modules_repo.repo_path}/{module}'")
            self.clear_component_dir(module, module_dir)
            install_track = nf_core.components.components_install.clean_modules_json(
                module, self.component_type, self.modules_repo, modules_json
            )

        log.info(f"{'Rei' if self.force else 'I'}nstalling '{module}'")
        log.debug(f"Installing module '{module}' at modules hash {version} from {self.modules_repo.remote_url}")

        # Download module files
        if not self.install_component_files(module, version, self.modules_repo, install_folder):
            return False

        if not silent:
            # Print include statement
            module_name = "_".join(module.upper().split("/"))
            log.info(
                f"Include statement: include {{ {module_name} }} from '.{os.path.join(install_folder, module)}/main'"
            )

        # Update module.json with newly installed module
        modules_json.load()
        modules_json.update(self.component_type, self.modules_repo, module, version, self.installed_by, install_track)
        return True
