import logging
import os

import questionary

import nf_core.modules.module_utils
import nf_core.utils

from .modules_command import ModuleCommand
from .modules_repo import NF_CORE_MODULES_NAME

log = logging.getLogger(__name__)


class ModuleInstall(ModuleCommand):
    def __init__(self, pipeline_dir, force=False, prompt=False, sha=None, update_all=False):
        super().__init__(pipeline_dir)
        self.force = force
        self.prompt = prompt
        self.sha = sha
        self.update_all = update_all

    def install(self, module):
        if self.repo_type == "modules":
            log.error("You cannot install a module in a clone of nf-core/modules")
            return False
        # Check whether pipelines is valid
        if not self.has_valid_directory():
            return False

        # Verify that 'modules.json' is consistent with the installed modules
        self.modules_json_up_to_date()

        if self.prompt and self.sha is not None:
            log.error("Cannot use '--sha' and '--prompt' at the same time!")
            return False

        # Verify that the provided SHA exists in the repo
        if self.sha:
            if not self.modules_repo.sha_exists_on_branch(self.sha):
                log.error(f"Commit SHA '{self.sha}' doesn't exist in '{self.modules_repo.fullname}'")
                return False

        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.modules_repo.get_avail_modules(),
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Check that the supplied name is an available module
        if module and module not in self.modules_repo.get_avail_modules():
            log.error(f"Module '{module}' not found in list of available modules.")
            log.info("Use the command 'nf-core modules list' to view available software")
            return False

        # Load 'modules.json'
        modules_json = self.load_modules_json()
        if not modules_json:
            return False

        if not self.modules_repo.module_exists(module):
            warn_msg = (
                f"Module '{module}' not found in remote '{self.modules_repo.fullname}' ({self.modules_repo.branch})"
            )
            log.warning(warn_msg)
            return False

        if self.modules_repo.fullname in modules_json["repos"]:
            current_entry = modules_json["repos"][self.modules_repo.fullname].get(module)
        else:
            current_entry = None

        # Set the install folder based on the repository name
        install_folder = [self.dir, "modules"]
        install_folder.extend(os.path.split(self.modules_repo.fullname))

        # Compute the module directory
        module_dir = os.path.join(*install_folder, module)

        # Check that the module is not already installed
        if (current_entry is not None and os.path.exists(module_dir)) and not self.force:

            log.error("Module is already installed.")
            repo_flag = (
                "" if self.modules_repo.fullname == NF_CORE_MODULES_NAME else f"-g {self.modules_repo.fullname} "
            )
            branch_flag = "" if self.modules_repo.branch == "master" else f"-b {self.modules_repo.branch} "

            log.info(
                f"To update '{module}' run 'nf-core modules {repo_flag}{branch_flag}update {module}'. To force reinstallation use '--force'"
            )
            return False

        if self.sha:
            version = self.sha
        elif self.prompt:
            try:
                version = nf_core.modules.module_utils.prompt_module_version_sha(
                    module,
                    installed_sha=current_entry["git_sha"] if not current_entry is None else None,
                    modules_repo=self.modules_repo,
                )
            except SystemError as e:
                log.error(e)
                return False
        else:
            # Fetch the latest commit for the module
            git_log = list(self.modules_repo.get_module_git_log(module, depth=1))
            version = git_log[0]["git_sha"]

        if self.force:
            log.info(f"Removing installed version of '{self.modules_repo.fullname}/{module}'")
            self.clear_module_dir(module, module_dir)

        log.info(f"{'Rei' if self.force else 'I'}nstalling '{module}'")
        log.debug(f"Installing module '{module}' at modules hash {version} from {self.modules_repo.fullname}")

        # Download module files
        if not self.install_module_files(module, version, self.modules_repo, install_folder):
            return False

        # Print include statement
        module_name = "_".join(module.upper().split("/"))
        log.info(f"Include statement: include {{ {module_name} }} from '.{os.path.join(*install_folder, module)}/main’")

        # Update module.json with newly installed module
        self.update_modules_json(modules_json, self.modules_repo, module, version)
        return True
