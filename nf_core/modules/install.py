import os
import questionary
import logging

import nf_core.utils

from .modules_command import ModuleCommand
from .module_utils import get_installed_modules, get_module_git_log, module_exist_in_repo
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleInstall(ModuleCommand):
    def __init__(self, pipeline_dir, force=False, latest=False, sha=None, update_all=False):
        super().__init__(pipeline_dir)
        self.force = force
        self.latest = latest
        self.sha = sha
        self.update_all = update_all

    def install(self, module):
        if self.repo_type == "modules":
            log.error("You cannot install a module in a clone of nf-core/modules")
            return False
        # Check whether pipelines is valid
        self.has_valid_directory()
        if not self.update_all:
            # Get the available modules
            try:
                self.modules_repo.get_modules_file_tree()
            except LookupError as e:
                log.error(e)
                return False

            if self.latest and self.sha is not None:
                log.error("Cannot use '--sha' and '--latest' at the same time!")
                return False

            if module is None:
                module = questionary.autocomplete(
                    "Tool name:",
                    choices=self.modules_repo.modules_avail_module_names,
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()

            # Check that the supplied name is an available module
            if module and module not in self.modules_repo.modules_avail_module_names:
                log.error("Module '{}' not found in list of available modules.".format(module))
                log.info("Use the command 'nf-core modules list' to view available software")
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
                if current_version == latest_version and (not self.force or self.latest or self.update_all):
                    log.info(f"'{modules_repo.name}/{module}' is already up to date")
                    continue
                elif not self.force:
                    log.error("Found newer version of module.")
                    self.latest = self.force = questionary.confirm(
                        "Do you want to install it? (--force --latest)", default=False
                    ).unsafe_ask()
                    if not self.latest:
                        exit_value = False
                        continue
            else:
                latest_version = None

            # Check that we don't already have a folder for this module
            if not self.check_module_files_installed(module, module_dir):
                exit_value = False
                continue

            if self.sha:
                if current_entry is not None:
                    if self.force:
                        if current_entry["git_sha"] == self.sha:
                            log.info(f"Module {modules_repo.name}/{module} already installed at {self.sha}")
                            continue
                    else:
                        exit_value = False
                        continue

                if self.force:
                    log.info(f"Removing old version of module '{module}'")
                    self.clear_module_dir(module, module_dir)

                if self.download_module_file(module, self.sha, modules_repo, install_folder, module_dir):
                    self.update_modules_json(modules_json, modules_repo.name, module, self.sha)
                else:
                    exit_value = False
                continue
            else:
                if self.latest or self.update_all:
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
                        version = self.prompt_module_version_sha(
                            module,
                            installed_sha=current_entry["git_sha"] if not current_entry is None else None,
                            modules_repo=modules_repo,
                        )
                    except SystemError as e:
                        log.error(e)
                        exit_value = False
                        continue
            log.info(f"Installing {module}")
            log.debug(
                f"Installing module '{module}' at modules hash {modules_repo.modules_current_hash} from {self.modules_repo.name}"
            )

            if self.force:
                log.info(f"Removing old version of module '{module}'")
                self.clear_module_dir(module, module_dir)

            # Download module files
            if not self.download_module_file(module, version, modules_repo, install_folder, module_dir):
                exit_value = False
                continue

            # Update module.json with newly installed module
            self.update_modules_json(modules_json, modules_repo.name, module, version)
        return exit_value

    def check_module_files_installed(self, module_name, module_dir):
        """Checks if a module is already installed"""
        if os.path.exists(module_dir):
            if not self.force:
                log.error(f"Module directory '{module_dir}' already exists.")
                self.force = questionary.confirm(
                    "Do you want to overwrite local files? (--force)", default=False
                ).unsafe_ask()
            return self.force
        else:
            return True

    def prompt_module_version_sha(self, module, installed_sha=None, modules_repo=None):
        if modules_repo is None:
            modules_repo = self.modules_repo
        older_commits_choice = questionary.Choice(
            title=[("fg:ansiyellow", "older commits"), ("class:choice-default", "")], value=""
        )
        git_sha = ""
        page_nbr = 1
        try:
            next_page_commits = get_module_git_log(module, modules_repo=modules_repo, per_page=10, page_nbr=page_nbr)
        except UserWarning:
            next_page_commits = None
        except LookupError as e:
            log.warning(e)
            next_page_commits = None

        while git_sha is "":
            commits = next_page_commits
            try:
                next_page_commits = get_module_git_log(
                    module, modules_repo=modules_repo, per_page=10, page_nbr=page_nbr + 1
                )
            except UserWarning:
                next_page_commits = None
            except LookupError as e:
                log.warning(e)
                next_page_commits = None

            choices = []
            for title, sha in map(lambda commit: (commit["trunc_message"], commit["git_sha"]), commits):

                display_color = "fg:ansiblue" if sha != installed_sha else "fg:ansired"
                message = f"{title} {sha}"
                if installed_sha == sha:
                    message += " (installed version)"
                commit_display = [(display_color, message), ("class:choice-default", "")]
                choices.append(questionary.Choice(title=commit_display, value=sha))
            if next_page_commits is not None:
                choices += [older_commits_choice]
            git_sha = questionary.select(
                f"Select '{module}' version:", choices=choices, style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()
            page_nbr += 1
        return git_sha
