import os
import questionary
import logging

import nf_core.utils
import nf_core.modules.module_utils

from .modules_command import ModuleCommand
from .module_utils import get_installed_modules, get_module_git_log, module_exist_in_repo
from .modules_repo import ModulesRepo

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

        # Loads the tools config
        tool_config = nf_core.utils.load_tools_config()
        update_config = tool_config.get("install", {})

        # Get the available modules
        try:
            self.modules_repo.get_modules_file_tree()
        except LookupError as e:
            log.error(e)
            return False

        if self.prompt and self.sha is not None:
            log.error("Cannot use '--sha' and '--prompt' at the same time!")
            return False

        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.modules_repo.modules_avail_module_names,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        if (
            module in update_config.get(self.modules_repo.name, {})
            and update_config[self.modules_repo.name].get(module) is False
        ):
            log.error("Module's install entry in '.nf-core.yml' is set to False")
            return False

        # Check that the supplied name is an available module
        if module and module not in self.modules_repo.modules_avail_module_names:
            log.error("Module '{}' not found in list of available modules.".format(module))
            log.info("Use the command 'nf-core modules list' to view available software")
            return False

        # Load 'modules.json'
        modules_json = self.load_modules_json()
        if not modules_json:
            return False

        if not module_exist_in_repo(module, self.modules_repo):
            warn_msg = f"Module '{module}' not found in remote '{self.modules_repo.name}' ({self.modules_repo.branch})"
            log.warning(warn_msg)
            return False

        if self.modules_repo.name in modules_json["repos"]:
            current_entry = modules_json["repos"][self.modules_repo.name].get(module)
        else:
            current_entry = None

        # Set the install folder based on the repository name
        install_folder = [self.modules_repo.owner, self.modules_repo.repo]

        # Compute the module directory
        module_dir = os.path.join(self.dir, "modules", *install_folder, module)

        # Check that the module is not already installed
        if (current_entry is not None and os.path.exists(module_dir)) and not self.force:

            log.error(f"Module is already installed.")
            repo_flag = "" if self.modules_repo.name == "nf-core/modules" else f"-g {self.modules_repo.name} "
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
            try:
                git_log = get_module_git_log(module, modules_repo=self.modules_repo, per_page=1, page_nbr=1)
            except UserWarning:
                log.error(f"Was unable to fetch version of module '{module}'")
                return False
            version = git_log[0]["git_sha"]

        if self.force:
            log.info(f"Removing installed version of '{self.modules_repo.name}/{module}'")
            self.clear_module_dir(module, module_dir)

        log.info(f"{'Rei' if self.force else 'I'}nstalling '{self.modules_repo.name}/{module}'")
        log.debug(
            f"Installing module '{module}' at modules hash {self.modules_repo.modules_current_hash} from {self.modules_repo.name}"
        )

        # Download module files
        if not self.download_module_file(module, version, self.modules_repo, install_folder, module_dir):
            return False

        # Update module.json with newly installed module
        self.update_modules_json(modules_json, self.modules_repo.name, module, version)
        return True
