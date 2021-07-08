import os
import questionary
import logging

import nf_core.utils

from .modules_command import ModuleCommand
from .module_utils import get_module_git_log

log = logging.getLogger(__name__)


class ModuleInstall(ModuleCommand):
    def __init__(self, pipeline_dir, force=False, latest=False, sha=None):
        super().__init__(pipeline_dir)
        self.force = force
        self.latest = latest
        self.sha = sha

    def install(self, module):
        if self.repo_type == "modules":
            log.error("You cannot install a module in a clone of nf-core/modules")
            return False
        # Check whether pipelines is valid
        self.has_valid_directory()

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
        if module not in self.modules_repo.modules_avail_module_names:
            log.error("Module '{}' not found in list of available modules.".format(module))
            log.info("Use the command 'nf-core modules list' to view available software")
            return False

        # Set the install folder based on the repository name
        install_folder = [self.modules_repo.owner, self.modules_repo.repo]

        # Compute the module directory
        module_dir = os.path.join(self.dir, "modules", *install_folder, module)

        # Load 'modules.json'
        modules_json = self.load_modules_json()
        if not modules_json:
            return False

        if self.modules_repo.name in modules_json["repos"]:
            current_entry = modules_json["repos"][self.modules_repo.name].get(module)
        else:
            current_entry = None

        if current_entry is not None and self.sha is None:
            # Fetch the latest commit for the module
            current_version = current_entry["git_sha"]
            try:
                git_log = get_module_git_log(module, modules_repo=self.modules_repo, per_page=1, page_nbr=1)
            except UserWarning:
                log.error(f"Was unable to fetch version of module '{module}'")
                return False
            latest_version = git_log[0]["git_sha"]
            if current_version == latest_version and not self.force:
                log.info("Already up to date")
                return True
            elif not self.force:
                log.error("Found newer version of module.")
                self.latest = self.force = questionary.confirm(
                    "Do you want install it? (--force --latest)", default=False
                ).unsafe_ask()
                if not self.latest:
                    return False
        else:
            latest_version = None

        # Check that we don't already have a folder for this module
        if not self.check_module_files_installed(module, module_dir):
            return False

        if self.sha:
            if not current_entry is None and not self.force:
                return False
            if self.download_module_file(module, self.sha, install_folder, module_dir):
                self.update_modules_json(modules_json, module, self.sha)
                return True
            else:
                try:
                    version = self.prompt_module_version_sha(
                        module, installed_sha=current_entry["git_sha"] if not current_entry is None else None
                    )
                except SystemError as e:
                    log.error(e)
                    return False
        else:
            if self.latest:
                # Fetch the latest commit for the module
                if latest_version is None:
                    try:
                        git_log = get_module_git_log(module, modules_repo=self.modules_repo, per_page=1, page_nbr=1)
                    except UserWarning:
                        log.error(f"Was unable to fetch version of module '{module}'")
                        return False
                    latest_version = git_log[0]["git_sha"]
                version = latest_version
            else:
                try:
                    version = self.prompt_module_version_sha(
                        module, installed_sha=current_entry["git_sha"] if not current_entry is None else None
                    )
                except SystemError as e:
                    log.error(e)
                    return False

        log.info(f"Installing {module}")
        log.debug(
            f"Installing module '{module}' at modules hash {self.modules_repo.modules_current_hash} from {self.modules_repo.name}"
        )

        # Download module files
        if not self.download_module_file(module, version, install_folder, module_dir):
            return False

        # Update module.json with newly installed module
        self.update_modules_json(modules_json, self.modules_repo.name, module, version)
        return True

    def check_module_files_installed(self, module_name, module_dir):
        """Checks if a module is already installed"""
        if os.path.exists(module_dir):
            if not self.force:
                log.error(f"Module directory '{module_dir}' already exists.")
                self.force = questionary.confirm(
                    "Do you want to overwrite local files? (--force)", default=False
                ).unsafe_ask()
            if self.force:
                log.info(f"Removing old version of module '{module_name}'")
                return self.clear_module_dir(module_name, module_dir)
            else:
                return False
        else:
            return True

    def prompt_module_version_sha(self, module, installed_sha=None):
        older_commits_choice = questionary.Choice(
            title=[("fg:ansiyellow", "older commits"), ("class:choice-default", "")], value=""
        )
        git_sha = ""
        page_nbr = 1
        try:
            next_page_commits = get_module_git_log(
                module, modules_repo=self.modules_repo, per_page=10, page_nbr=page_nbr
            )
        except UserWarning:
            next_page_commits = None

        while git_sha is "":
            commits = next_page_commits
            try:
                next_page_commits = get_module_git_log(
                    module, modules_repo=self.modules_repo, per_page=10, page_nbr=page_nbr + 1
                )
            except UserWarning:
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
                f"Select '{module}' version", choices=choices, style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()
            page_nbr += 1
        return git_sha
