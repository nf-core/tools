import difflib
import enum
import json
import logging
import os
import shutil
import tempfile

import questionary
from rich.console import Console
from rich.syntax import Syntax

import nf_core.modules.module_utils
import nf_core.utils
from nf_core.utils import plural_s, plural_y

from .modules_command import ModuleCommand
from .modules_json import ModulesJson
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleUpdate(ModuleCommand):
    def __init__(
        self,
        pipeline_dir,
        force=False,
        prompt=False,
        sha=None,
        update_all=False,
        show_diff=None,
        save_diff_fn=None,
        remote_url=None,
        branch=None,
        no_pull=False,
        base_path=None,
    ):
        super().__init__(pipeline_dir, remote_url, branch, no_pull, base_path)
        self.force = force
        self.prompt = prompt
        self.sha = sha
        self.update_all = update_all
        self.show_diff = show_diff
        self.save_diff_fn = save_diff_fn
        self.module = None
        self.update_config = None
        self.module_json = None

    def _parameter_checks(self):
        """Check the compatibilty of the supplied parameters.

        Checks:
            - Either `--preview` or `--save_diff` can be specified, not both.
        """

        if self.save_diff_fn and self.show_diff:
            raise UserWarning("Either `--preview` or `--save_diff` can be specified, not both.")

        if self.update_all and self.module:
            raise UserWarning("Either a module or the '--all' flag can be specified, not both.")

        if self.repo_type == "modules":
            raise UserWarning("Modules in clones of nf-core/modules can not be updated.")

        if self.prompt and self.sha is not None:
            raise UserWarning("Cannot use '--sha' and '--prompt' at the same time.")

        if not self.has_valid_directory():
            raise UserWarning("The command was not run in a valid pipeline directory.")

    def get_single_module_info(self, module):
        """
        Get modules repo and module verion info for a single module.

        Information about the module version in the '.nf-core.yml' overrides
        the '--sha' option

        Args:
            module_name (str): The name of the module to get info for.

        Returns:
            (ModulesRepo, str, str): The modules repo containing the module,
            the module name, and the module version.

        Raises:
            LookupError: If the module is not found either in the pipeline or the modules repo.
            UserWarning: If the '.nf-core.yml' entry is not valid.
        """
        # Check if there are any modules installed from the repo
        repo_name = self.modules_repo.fullname
        if repo_name not in self.module_names:
            raise LookupError(f"No modules installed from '{repo_name}'")

        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.module_names[repo_name],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Check if module is installed before trying to update
        if module not in self.module_names[repo_name]:
            raise LookupError(f"Module '{module}' is not installed in pipeline and could therefore not be updated")

        # Check that the supplied name is an available module
        if module and module not in self.modules_repo.get_avail_modules():
            raise LookupError(
                f"Module '{module}' not found in list of available modules."
                f"Use the command 'nf-core modules list remote' to view available software"
            )

        sha = self.sha
        if module in self.update_config.get(self.modules_repo.fullname, {}):
            config_entry = self.update_config[self.modules_repo.fullname].get(module)
            if config_entry is not None and config_entry is not True:
                if config_entry is False:
                    raise UserWarning("Module's update entry in '.nf-core.yml' is set to False")
                if not isinstance(config_entry, str):
                    raise UserWarning("Module's update entry in '.nf-core.yml' is of wrong type")

                sha = config_entry
                if self.sha is not None:
                    log.warning(
                        f"Found entry in '.nf-core.yml' for module '{module}' "
                        "which will override version specified with '--sha'"
                    )
                else:
                    log.info(f"Found entry in '.nf-core.yml' for module '{module}'")
                log.info(f"Updating module to ({sha})")

        return (self.modules_repo, module, sha)

    def get_all_modules_info(self):
        """
        Get modules repo and module version information for all modules.

        Information about the module version in the '.nf-core.yml' overrides
        the '--sha' option

        Returns:
            [(ModulesRepo, str, str)]: A list of tuples containing a ModulesRepo object,
            the module name, and the module version.
        """
        skipped_repos = []
        skipped_modules = []
        overridden_repos = []
        overridden_modules = []
        repos_mods_shas = {}
        # Loop through all the modules in the pipeline
        # and check if they have an entry in the '.nf-core.yml' file
        for repo_name, modules in self.module_names.items():
            if repo_name not in self.update_config or self.update_config[repo_name] is True:
                repos_mods_shas[repo_name] = [(module, self.sha) for module in modules]
            elif isinstance(self.update_config[repo_name], dict):
                # If it is a dict, then there are entries for individual modules
                repo_config = self.update_config[repo_name]
                repos_mods_shas[repo_name] = []
                for module in modules:
                    if module not in repo_config or repo_config[module] is True:
                        repos_mods_shas[repo_name].append((module, self.sha))
                    elif isinstance(repo_config[module], str):
                        # If a string is given it is the commit SHA to which we should update to
                        custom_sha = repo_config[module]
                        repos_mods_shas[repo_name].append((module, custom_sha))
                        if self.sha is not None:
                            overridden_modules.append(module)
                    elif repo_config[module] is False:
                        # Otherwise the entry must be 'False' and we should ignore the module
                        skipped_modules.append(f"{repo_name}/{module}")
                    else:
                        raise UserWarning(f"Module '{module}' in '{repo_name}' has an invalid entry in '.nf-core.yml'")
            elif isinstance(self.update_config[repo_name], str):
                # If a string is given it is the commit SHA to which we should update to
                custom_sha = self.update_config[repo_name]
                repos_mods_shas[repo_name] = [(module_name, custom_sha) for module_name in modules]
                if self.sha is not None:
                    overridden_repos.append(repo_name)
            elif self.update_config[repo_name] is False:
                skipped_repos.append(repo_name)
            else:
                raise UserWarning(f"Repo '{repo_name}' has an invalid entry in '.nf-core.yml'")

        if skipped_repos:
            skipped_str = "', '".join(skipped_repos)
            log.info(f"Skipping modules in repositor{plural_y(skipped_repos)}: '{skipped_str}'")

        if skipped_modules:
            skipped_str = "', '".join(skipped_modules)
            log.info(f"Skipping module{plural_s(skipped_modules)}: '{skipped_str}'")

        if overridden_repos:
            overridden_str = "', '".join(overridden_repos)
            log.info(
                f"Overriding '--sha' flag for modules in repositor{plural_y(overridden_repos)} "
                f"with '.nf-core.yml' entry: '{overridden_str}'"
            )

        if overridden_modules:
            overridden_str = "', '".join(overridden_modules)
            log.info(
                f"Overriding '--sha' flag for module{plural_s(overridden_modules)} with '.nf-core.yml' entry: '{overridden_str}'"
            )

        # Get the git urls from the modules.json
        repos_mods_shas = [
            (self.modules_json.get_git_url(repo_name), self.modules_json.get_base_path(repo_name), mods_shas)
            for repo_name, mods_shas in repos_mods_shas.items()
        ]

        # Create ModulesRepo objects
        repos_mods_shas = [
            (ModulesRepo(remote_url=repo_url, base_path=base_path), mods_shas)
            for repo_url, base_path, mods_shas in repos_mods_shas
        ]

        # Flatten the list
        repos_mods_shas = [(repo, mod, sha) for repo, mods_shas in repos_mods_shas for mod, sha in mods_shas]

    def update(self, module=None):

        self.module = module

        tool_config = nf_core.utils.load_tools_config(self.dir)
        self.update_config = tool_config.get("update", {})

        self._parameter_checks()

        # Verify that 'modules.json' is consistent with the installed modules
        self.modules_json = ModulesJson(self.dir)
        self.modules_json.check_up_to_date()

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

        # Verify that the provided SHA exists in the repo
        if self.sha and not self.modules_repo.sha_exists_on_branch(self.sha):
            log.error(f"Commit SHA '{self.sha}' doesn't exist in '{self.modules_repo.fullname}'")
            return False

        self.get_pipeline_modules()
        repos_mods_shas = self.get_all_modules_info() if self.update_all else [self.get_single_module_info()]

        # Save the current state of the modules.json
        old_modules_json = self.modules_json.get_modules_json()

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
                    "Enter a new filename: ",
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()

        exit_value = True
        for modules_repo, module, sha in repos_mods_shas:

            # Are we updating the files in place or not?
            dry_run = self.show_diff or self.save_diff_fn

            # Check if the module we've been asked to update actually exists
            if not modules_repo.module_exists(module):
                warn_msg = f"Module '{module}' not found in remote '{modules_repo.fullname}' ({modules_repo.branch})"
                if self.update_all:
                    warn_msg += ". Skipping..."
                log.warning(warn_msg)
                exit_value = False
                continue

            current_version = self.modules_json.get_module_version(module, modules_repo.fullname)

            # Set the install folder based on the repository name
            install_folder = [self.dir, "modules"]
            install_folder.extend(os.path.split(modules_repo.fullname))

            # Compute the module directory
            module_dir = os.path.join(*install_folder, module)

            if sha:
                version = sha
            elif self.prompt:
                try:
                    version = nf_core.modules.module_utils.prompt_module_version_sha(
                        module, modules_repo=modules_repo, installed_sha=current_version
                    )
                except SystemError as e:
                    log.error(e)
                    exit_value = False
                    continue
            else:
                # Fetch the latest commit for the module
                git_log = list(modules_repo.get_module_git_log(module, depth=1))
                version = git_log[0]["git_sha"]

            if current_version is not None and not self.force:
                # Fetch the latest commit for the module
                if current_version == version:
                    if self.sha or self.prompt:
                        log.info(f"'{modules_repo.fullname}/{module}' is already installed at {version}")
                    else:
                        log.info(f"'{modules_repo.fullname}/{module}' is already up to date")
                    continue

            if dry_run:
                # Set the install folder to a temporary directory
                install_folder = [tempfile.mkdtemp()]
            else:
                log.info(f"Updating '{modules_repo.fullname}/{module}'")
                log.debug(f"Updating module '{module}' to {version} from {modules_repo.remote_url}")

                log.debug(f"Removing old version of module '{module}'")
                self.clear_module_dir(module, module_dir)

            # Download module files
            if not self.install_module_files(module, version, modules_repo, install_folder):
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
                            f"Changes in module '{module}' between"
                            f" ({current_version if current_version is not None else '?'}) and"
                            f" ({version if version is not None else 'latest'})\n"
                        )

                        for file, (diff_status, diff) in diffs.items():
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
                        f"Changes in module '{module}' between"
                        f" ({current_version if current_version is not None else '?'}) and"
                        f" ({version if version is not None else 'latest'})"
                    )

                    for file, (diff_status, diff) in diffs.items():
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
                        log.info(f"Updating '{modules_repo.fullname}/{module}'")
                        log.debug(f"Updating module '{module}' to {version} from {modules_repo.fullname}")

            # Update modules.json with newly installed module
            if not dry_run:
                self.modules_json.update(modules_repo, module, version)

            # Don't save to a file, just iteratively update the variable
            else:
                self.modules_json.update(modules_repo, module, version, write_file=False)

        if self.save_diff_fn:
            # Compare the new modules.json and build a diff
            modules_json_diff = difflib.unified_diff(
                json.dumps(old_modules_json, indent=4).splitlines(keepends=True),
                json.dumps(self.modules_json.get_modules_json(), indent=4).splitlines(keepends=True),
                fromfile=os.path.join(self.dir, "modules.json"),
                tofile=os.path.join(self.dir, "modules.json"),
            )

            # Save diff for modules.json to file
            with open(self.save_diff_fn, "a") as fh:
                fh.write("Changes in './modules.json'\n")
                for line in modules_json_diff:
                    fh.write(line)
                fh.write("*" * 60 + "\n")

            log.info(
                f"[bold magenta italic] TIP! [/] If you are happy with the changes in '{self.save_diff_fn}', you "
                "can apply them by running the command :point_right:"
                f"  [bold magenta italic]git apply {self.save_diff_fn} [/]"
            )

        else:

            log.info("Updates complete :sparkles:")

        return exit_value
