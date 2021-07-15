import os
import questionary
import logging

import nf_core.utils
import nf_core.modules.module_utils

from .modules_command import ModuleCommand
from .module_utils import get_installed_modules, get_module_git_log, module_exist_in_repo
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleUpdate(ModuleCommand):
    def __init__(self, pipeline_dir, force=False, prompt=False, sha=None, update_all=False):
        super().__init__(pipeline_dir)
        self.force = force
        self.prompt = prompt
        self.sha = sha
        self.update_all = update_all

    def update(self, module):
        if self.repo_type == "modules":
            log.error("You cannot update a module in a clone of nf-core/modules")
            return False
        # Check whether pipelines is valid
        if not self.has_valid_directory():
            return False

        # Verify that 'modules.json' is consistent with the installed modules
        self.modules_json_up_to_date()

        if not self.update_all:
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
                self.get_pipeline_modules()
                repo_name = self.modules_repo.name
                if repo_name not in self.module_names:
                    log.error(f"No modules installed from '{repo_name}'")
                    return False
                module = questionary.autocomplete(
                    "Tool name:",
                    choices=self.module_names[repo_name],
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()

            # Check that the supplied name is an available module
            if module and module not in self.modules_repo.modules_avail_module_names:
                log.error("Module '{}' not found in list of available modules.".format(module))
                log.info("Use the command 'nf-core modules list remote' to view available software")
                return False

            repos_and_modules = [(self.modules_repo, module)]
        else:
            if module:
                raise UserWarning("You cannot specify a module and use the '--all' flag at the same time")
            self.force = True

            self.get_pipeline_modules()
            repos_and_modules = [
                (ModulesRepo(repo=repo_name), modules) for repo_name, modules in self.module_names.items()
            ]
            # Load the modules file trees
            for repo, _ in repos_and_modules:
                repo.get_modules_file_tree()
            repos_and_modules = [(repo, module) for repo, modules in repos_and_modules for module in modules]

        # Load 'modules.json'
        modules_json = self.load_modules_json()
        if not modules_json:
            return False

        exit_value = True
        for modules_repo, module in repos_and_modules:
            if not module_exist_in_repo(module, modules_repo):
                warn_msg = f"Module '{module}' not found in remote '{modules_repo.name}' ({modules_repo.branch})"
                if self.update_all:
                    warn_msg += ". Skipping..."
                log.warning(warn_msg)
                exit_value = False
                continue

            if modules_repo.name in modules_json["repos"]:
                current_entry = modules_json["repos"][modules_repo.name].get(module)
            else:
                current_entry = None

            # Set the install folder based on the repository name
            install_folder = [modules_repo.owner, modules_repo.repo]

            # Compute the module directory
            module_dir = os.path.join(self.dir, "modules", *install_folder, module)

            if current_entry is not None and self.sha is None:
                # Fetch the latest commit for the module
                current_version = current_entry["git_sha"]
                try:
                    git_log = get_module_git_log(module, modules_repo=modules_repo, per_page=1, page_nbr=1)
                except LookupError as e:
                    log.error(e)
                    exit_value = False
                    continue
                except UserWarning:
                    log.error(f"Was unable to fetch version of '{modules_repo.name}/{module}'")
                    exit_value = False
                    continue
                latest_version = git_log[0]["git_sha"]
                if current_version == latest_version and not self.prompt:
                    log.info(f"'{modules_repo.name}/{module}' is already up to date")
                    continue
            else:
                latest_version = None

            if self.sha:
                if current_entry is not None and not self.force:
                    if current_entry["git_sha"] == self.sha:
                        log.info(f"Module {modules_repo.name}/{module} already installed at {self.sha}")
                        continue

                # Remove installed module files
                log.info(f"Removing old version of module '{module}'")
                self.clear_module_dir(module, module_dir)

                if self.download_module_file(module, self.sha, modules_repo, install_folder, module_dir):
                    self.update_modules_json(modules_json, modules_repo.name, module, self.sha)
                else:
                    exit_value = False
                continue
            else:
                if not self.prompt:
                    # Fetch the latest commit for the module
                    if latest_version is None:
                        try:
                            git_log = get_module_git_log(module, modules_repo=modules_repo, per_page=1, page_nbr=1)
                        except UserWarning:
                            log.error(f"Was unable to fetch version of module '{module}'")
                            exit_value = False
                            continue
                        latest_version = git_log[0]["git_sha"]
                    version = latest_version
                else:
                    try:
                        version = nf_core.modules.module_utils.prompt_module_version_sha(
                            module,
                            modules_repo=modules_repo,
                            installed_sha=current_entry["git_sha"] if not current_entry is None else None,
                        )
                    except SystemError as e:
                        log.error(e)
                        exit_value = False
                        continue

            log.info(f"Updating '{modules_repo.name}/{module}'")
            log.debug(
                f"Updating module '{module}' to {modules_repo.modules_current_hash} from {self.modules_repo.name}"
            )

            log.debug(f"Removing old version of module '{module}'")
            self.clear_module_dir(module, module_dir)

            # Download module files
            if not self.download_module_file(module, version, modules_repo, install_folder, module_dir):
                exit_value = False
                continue

            # Update module.json with newly installed module
            self.update_modules_json(modules_json, modules_repo.name, module, version)
        return exit_value
