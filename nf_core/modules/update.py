import copy
import difflib
import enum
import json
import logging
import os
import questionary
import shutil
import tempfile
from questionary import question
from rich.console import Console
from rich.syntax import Syntax

import nf_core.utils
import nf_core.modules.module_utils

from .modules_command import ModuleCommand
from .module_utils import get_installed_modules, get_module_git_log, module_exist_in_repo
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleUpdate(ModuleCommand):
    def __init__(
        self, pipeline_dir, force=False, prompt=False, sha=None, update_all=False, show_diff=None, save_diff_fn=None
    ):
        super().__init__(pipeline_dir)
        self.force = force
        self.prompt = prompt
        self.sha = sha
        self.update_all = update_all
        self.show_diff = show_diff
        self.save_diff_fn = save_diff_fn

    def update(self, module):
        if self.repo_type == "modules":
            log.error("You cannot update a module in a clone of nf-core/modules")
            return False
        # Check whether pipelines is valid
        if not self.has_valid_directory():
            return False

        # Verify that 'modules.json' is consistent with the installed modules
        self.modules_json_up_to_date()

        tool_config = nf_core.utils.load_tools_config()
        update_config = tool_config.get("update", {})
        if not self.update_all and module is None:
            choices = ["All modules", "Named module"]
            self.update_all = (
                questionary.select(
                    "Update all modules or a single named module?",
                    choices=choices,
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()
                == "All modules"
            )

        if self.prompt and self.sha is not None:
            log.error("Cannot use '--sha' and '--prompt' at the same time!")
            return False

        # Verify that the provided SHA exists in the repo
        if self.sha:
            try:
                nf_core.modules.module_utils.sha_exists(self.sha, self.modules_repo)
            except UserWarning:
                log.error(f"Commit SHA '{self.sha}' doesn't exist in '{self.modules_repo.name}'")
                return False
            except LookupError as e:
                log.error(e)
                return False

        if not self.update_all:
            # Get the available modules
            try:
                self.modules_repo.get_modules_file_tree()
            except LookupError as e:
                log.error(e)
                return False

            # Check if there are any modules installed from
            repo_name = self.modules_repo.name
            if repo_name not in self.module_names:
                log.error(f"No modules installed from '{repo_name}'")
                return False

            if module is None:
                self.get_pipeline_modules()
                module = questionary.autocomplete(
                    "Tool name:",
                    choices=self.module_names[repo_name],
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()

            # Check if module is installed before trying to update
            if module not in self.module_names[repo_name]:
                log.error(f"Module '{module}' is not installed in pipeline and could therefore not be updated")
                return False

            sha = self.sha
            if module in update_config.get(self.modules_repo.name, {}):
                config_entry = update_config[self.modules_repo.name].get(module)
                if config_entry is not None and config_entry is not True:
                    if config_entry is False:
                        log.info("Module's update entry in '.nf-core.yml' is set to False")
                        return False
                    elif isinstance(config_entry, str):
                        sha = config_entry
                        if self.sha:
                            log.warning(
                                f"Found entry in '.nf-core.yml' for module '{module}' "
                                "which will override version specified with '--sha'"
                            )
                        else:
                            log.info(f"Found entry in '.nf-core.yml' for module '{module}'")
                        log.info(f"Updating module to ({sha})")
                    else:
                        log.error("Module's update entry in '.nf-core.yml' is of wrong type")
                        return False

            # Check that the supplied name is an available module
            if module and module not in self.modules_repo.modules_avail_module_names:
                log.error("Module '{}' not found in list of available modules.".format(module))
                log.info("Use the command 'nf-core modules list remote' to view available software")
                return False

            repos_mods_shas = [(self.modules_repo, module, sha)]

        else:
            if module:
                raise UserWarning("You cannot specify a module and use the '--all' flag at the same time")

            self.get_pipeline_modules()

            # Filter out modules that should not be updated or assign versions if there are any
            skipped_repos = []
            skipped_modules = []
            repos_mods_shas = {}
            for repo_name, modules in self.module_names.items():
                if repo_name not in update_config or update_config[repo_name] is True:
                    repos_mods_shas[repo_name] = []
                    for module in modules:
                        repos_mods_shas[repo_name].append((module, self.sha))
                elif isinstance(update_config[repo_name], dict):
                    repo_config = update_config[repo_name]
                    repos_mods_shas[repo_name] = []
                    for module in modules:
                        if module not in repo_config or repo_config[module] is True:
                            repos_mods_shas[repo_name].append((module, self.sha))
                        elif isinstance(repo_config[module], str):
                            # If a string is given it is the commit SHA to which we should update to
                            custom_sha = repo_config[module]
                            repos_mods_shas[repo_name].append((module, custom_sha))
                        else:
                            # Otherwise the entry must be 'False' and we should ignore the module
                            skipped_modules.append(f"{repo_name}/{module}")
                elif isinstance(update_config[repo_name], str):
                    # If a string is given it is the commit SHA to which we should update to
                    custom_sha = update_config[repo_name]
                    repos_mods_shas[repo_name] = []
                    for module in modules:
                        repos_mods_shas[repo_name].append((module, custom_sha))
                else:
                    skipped_repos.append(repo_name)

            if skipped_repos:
                skipped_str = "', '".join(skipped_repos)
                log.info(f"Skipping modules in repositor{'y' if len(skipped_repos) == 1 else 'ies'}: '{skipped_str}'")

            if skipped_modules:
                skipped_str = "', '".join(skipped_modules)
                log.info(f"Skipping module{'' if len(skipped_modules) == 1 else 's'}: '{skipped_str}'")

            repos_mods_shas = [
                (ModulesRepo(repo=repo_name), mods_shas) for repo_name, mods_shas in repos_mods_shas.items()
            ]

            for repo, _ in repos_mods_shas:
                repo.get_modules_file_tree()

            # Flatten the list
            repos_mods_shas = [(repo, mod, sha) for repo, mods_shas in repos_mods_shas for mod, sha in mods_shas]

        # Load 'modules.json'
        modules_json = self.load_modules_json()
        old_modules_json = copy.deepcopy(modules_json)  # Deep copy to avoid mutability
        if not modules_json:
            return False

        # If --preview is true, don't save to a patch file
        if self.show_diff:
            self.show_diff_fn = False

        # Ask if we should show the diffs (unless a filename was already given on the command line)
        if not self.save_diff_fn and self.show_diff is None:
            diff_type = questionary.select(
                "Do you want to view diffs of the proposed changes?",
                choices=[
                    {"name": "No previews, just update everything", "value": 0},
                    {"name": "Preview diff in terminal, choose whether to update files", "value": 1},
                    {"name": "Just write diffs to a patch file", "value": 2},
                ],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

            self.show_diff = diff_type == 1
            self.save_diff_fn = diff_type == 2

        # Set up file to save diff
        if self.save_diff_fn:  # True or a string
            # From questionary - no filename yet
            if self.save_diff_fn is True:
                self.save_diff_fn = questionary.text(
                    "Enter the filename: ", style=nf_core.utils.nfcore_question_style
                ).unsafe_ask()
            # Check if filename already exists (questionary or cli)
            while os.path.exists(self.save_diff_fn):
                if questionary.confirm(f"'{self.save_diff_fn}' exists. Remove file?").unsafe_ask():
                    os.remove(self.save_diff_fn)
                    break
                self.save_diff_fn = questionary.text(
                    f"Enter a new filename: ",
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()

        exit_value = True
        for modules_repo, module, sha in repos_mods_shas:

            # Are we updating the files in place or not?
            dry_run = self.show_diff or self.save_diff_fn

            # Check if the module we've been asked to update actually exists
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
            install_folder = [self.dir, "modules", modules_repo.owner, modules_repo.repo]

            # Compute the module directory
            module_dir = os.path.join(*install_folder, module)

            if sha:
                version = sha
            elif self.prompt:
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
            else:
                # Fetch the latest commit for the module
                try:
                    git_log = get_module_git_log(module, modules_repo=modules_repo, per_page=1, page_nbr=1)
                except UserWarning:
                    log.error(f"Was unable to fetch version of module '{module}'")
                    exit_value = False
                    continue
                version = git_log[0]["git_sha"]

            if current_entry is not None and not self.force:
                # Fetch the latest commit for the module
                current_version = current_entry["git_sha"]
                if current_version == version:
                    if self.sha or self.prompt:
                        log.info(f"'{modules_repo.name}/{module}' is already installed at {version}")
                    else:
                        log.info(f"'{modules_repo.name}/{module}' is already up to date")
                    continue

            if not dry_run:
                log.info(f"Updating '{modules_repo.name}/{module}'")
                log.debug(f"Updating module '{module}' to {version} from {modules_repo.name}")

                log.debug(f"Removing old version of module '{module}'")
                self.clear_module_dir(module, module_dir)

            if dry_run:
                # Set the install folder to a temporary directory
                install_folder = ["/tmp", next(tempfile._get_candidate_names())]

            # Download module files
            if not self.download_module_file(module, version, modules_repo, install_folder, dry_run=dry_run):
                exit_value = False
                continue

            if dry_run:

                class DiffEnum(enum.Enum):
                    """
                    Enumeration for keeping track of
                    the diff status of a pair of files
                    """

                    UNCHANGED = enum.auto()
                    CHANGED = enum.auto()
                    CREATED = enum.auto()
                    REMOVED = enum.auto()

                diffs = {}

                # Get all unique filenames in the two folders.
                # `dict.fromkeys()` is used instead of `set()` to preserve order
                files = dict.fromkeys(os.listdir(os.path.join(*install_folder, module)))
                files.update(dict.fromkeys(os.listdir(module_dir)))
                files = list(files)

                temp_folder = os.path.join(*install_folder, module)

                # Loop through all the module files and compute their diffs if needed
                for file in files:
                    temp_path = os.path.join(temp_folder, file)
                    curr_path = os.path.join(module_dir, file)
                    if os.path.exists(temp_path) and os.path.exists(curr_path) and os.path.isfile(temp_path):
                        with open(temp_path, "r") as fh:
                            new_lines = fh.readlines()
                        with open(curr_path, "r") as fh:
                            old_lines = fh.readlines()

                        if new_lines == old_lines:
                            # The files are identical
                            diffs[file] = (DiffEnum.UNCHANGED, ())
                        else:
                            # Compute the diff
                            diff = difflib.unified_diff(
                                old_lines,
                                new_lines,
                                fromfile=os.path.join(module_dir, file),
                                tofile=os.path.join(module_dir, file),
                            )
                            diffs[file] = (DiffEnum.CHANGED, diff)

                    elif os.path.exists(temp_path):
                        # The file was created
                        diffs[file] = (DiffEnum.CREATED, ())

                    elif os.path.exists(curr_path):
                        # The file was removed
                        diffs[file] = (DiffEnum.REMOVED, ())

                if self.save_diff_fn:
                    log.info(f"Writing diff of '{module}' to '{self.save_diff_fn}'")
                    with open(self.save_diff_fn, "a") as fh:
                        fh.write(
                            f"Changes in module '{module}' between ({current_entry['git_sha'] if current_entry is not None else '?'}) and ({version if version is not None else 'latest'})\n"
                        )

                        for file, d in diffs.items():
                            diff_status, diff = d
                            if diff_status == DiffEnum.UNCHANGED:
                                # The files are identical
                                fh.write(f"'{os.path.join(module_dir, file)}' is unchanged\n")

                            elif diff_status == DiffEnum.CREATED:
                                # The file was created between the commits
                                fh.write(f"'{os.path.join(module_dir, file)}' was created\n")

                            elif diff_status == DiffEnum.REMOVED:
                                # The file was removed between the commits
                                fh.write(f"'{os.path.join(module_dir, file)}' was removed\n")

                            else:
                                # The file has changed
                                fh.write(f"Changes in '{os.path.join(module_dir, file)}':\n")
                                # Write the diff lines to the file
                                for line in diff:
                                    fh.write(line)
                                fh.write("\n")

                        fh.write("*" * 60 + "\n")
                elif self.show_diff:
                    console = Console(force_terminal=nf_core.utils.rich_force_colors())
                    log.info(
                        f"Changes in module '{module}' between ({current_entry['git_sha'] if current_entry is not None else '?'}) and ({version if version is not None else 'latest'})"
                    )

                    for file, d in diffs.items():
                        diff_status, diff = d
                        if diff_status == DiffEnum.UNCHANGED:
                            # The files are identical
                            log.info(f"'{os.path.join(module, file)}' is unchanged")
                        elif diff_status == DiffEnum.CREATED:
                            # The file was created between the commits
                            log.info(f"'{os.path.join(module, file)}' was created")
                        elif diff_status == DiffEnum.REMOVED:
                            # The file was removed between the commits
                            log.info(f"'{os.path.join(module, file)}' was removed")
                        else:
                            # The file has changed
                            log.info(f"Changes in '{os.path.join(module, file)}':")
                            # Pretty print the diff using the pygments diff lexer
                            console.print(Syntax("".join(diff), "diff", theme="ansi_light"))

                    # Ask the user if they want to install the module
                    dry_run = not questionary.confirm(
                        f"Update module '{module}'?", default=False, style=nf_core.utils.nfcore_question_style
                    ).unsafe_ask()
                    if not dry_run:
                        # The new module files are already installed.
                        # We just need to clear the directory and move the
                        # new files from the temporary directory
                        self.clear_module_dir(module, module_dir)
                        os.makedirs(module_dir)
                        for file in files:
                            path = os.path.join(temp_folder, file)
                            if os.path.exists(path):
                                shutil.move(path, os.path.join(module_dir, file))
                        log.info(f"Updating '{modules_repo.name}/{module}'")
                        log.debug(f"Updating module '{module}' to {version} from {modules_repo.name}")

            # Update modules.json with newly installed module
            if not dry_run:
                self.update_modules_json(modules_json, modules_repo.name, module, version)

            # Don't save to a file, just iteratively update the variable
            else:
                modules_json = self.update_modules_json(
                    modules_json, modules_repo.name, module, version, write_file=False
                )

        if self.save_diff_fn:
            # Compare the new modules.json and build a diff
            modules_json_diff = difflib.unified_diff(
                json.dumps(old_modules_json, indent=4).splitlines(keepends=True),
                json.dumps(modules_json, indent=4).splitlines(keepends=True),
                fromfile=os.path.join(self.dir, "modules.json"),
                tofile=os.path.join(self.dir, "modules.json"),
            )

            # Save diff for modules.json to file
            with open(self.save_diff_fn, "a") as fh:
                fh.write(f"Changes in './modules.json'\n")
                for line in modules_json_diff:
                    fh.write(line)
                fh.write("*" * 60 + "\n")

        log.info("Updates complete :sparkles:")

        if self.save_diff_fn:
            log.info(
                f"[bold magenta italic] TIP! [/] If you are happy with the changes in '{self.save_diff_fn}', you can apply them by running the command :point_right:  [bold magenta italic]git apply {self.save_diff_fn}"
            )

        return exit_value
