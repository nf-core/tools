import copy
import datetime
import json
import logging
import os
import shutil
from pathlib import Path

import git
import questionary
import rich.progress

import nf_core.modules.module_utils
import nf_core.modules.modules_repo
import nf_core.utils

log = logging.getLogger(__name__)


class ModulesJson:
    """
    An object for handling a 'modules.json' file in a pipeline
    """

    def __init__(self, pipeline_dir):
        """
        Initialise the object.

        Args:
            pipeline_dir (str): The pipeline directory
        """
        self.dir = pipeline_dir
        self.modules_dir = os.path.join(self.dir, "modules")
        self.modules_json = None
        self.pipeline_modules = None

    def create(self):
        """
        Creates the modules.json file from the modules installed in the pipeline directory

        Raises:
            UserWarning: If the creation fails
        """
        pipeline_config = nf_core.utils.fetch_wf_config(self.dir)
        pipeline_name = pipeline_config.get("manifest.name", "")
        pipeline_url = pipeline_config.get("manifest.homePage", "")
        modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "repos": dict()}
        modules_dir = f"{self.dir}/modules"

        if not os.path.exists(modules_dir):
            raise UserWarning("Can't find a ./modules directory. Is this a DSL2 pipeline?")

        repos = self.get_pipeline_module_repositories(Path(modules_dir))

        # Get all module names in the repos
        repo_module_names = [
            (
                repo_name,
                [
                    os.path.relpath(dir_name, os.path.join(modules_dir, repo_name))
                    for dir_name, _, file_names in os.walk(os.path.join(modules_dir, repo_name))
                    if "main.nf" in file_names
                ],
                repo_remote,
                base_path,
            )
            for repo_name, (repo_remote, base_path) in repos.items()
        ]
        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            n_total_modules = sum(len(modules) for _, modules, _, _ in repo_module_names)
            file_progress = progress_bar.add_task(
                "Creating 'modules.json' file", total=n_total_modules, test_name="module.json"
            )
            for repo_name, module_names, remote, base_path in sorted(repo_module_names):
                try:
                    # Create a ModulesRepo object without progress bar to not conflict with the other one
                    modules_repo = nf_core.modules.modules_repo.ModulesRepo(
                        remote_url=remote, base_path=base_path, no_progress=True
                    )
                except LookupError as e:
                    raise UserWarning(e)

                repo_path = os.path.join(modules_dir, repo_name)
                modules_json["repos"][repo_name] = dict()
                modules_json["repos"][repo_name]["git_url"] = remote
                modules_json["repos"][repo_name]["modules"] = dict()
                modules_json["repos"][repo_name]["base_path"] = base_path
                for module_name in sorted(module_names):
                    module_path = os.path.join(repo_path, module_name)
                    progress_bar.update(file_progress, advance=1, test_name=f"{repo_name}/{module_name}")
                    correct_commit_sha = self.find_correct_commit_sha(module_name, module_path, modules_repo)

                    modules_json["repos"][repo_name]["modules"][module_name] = {"git_sha": correct_commit_sha}

        modules_json_path = os.path.join(self.dir, "modules.json")
        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=4)
            fh.write("\n")

    def get_pipeline_module_repositories(self, modules_dir, repos=None):
        """
        Finds all module repositories in the modules directory. Ignores the local modules.
        Args:
            modules_dir (Path): base directory for the module files
        Returns
            repos [ (str, str, str) ]: List of tuples of repo name, repo remote URL and path to modules in repo
        """
        if repos is None:
            repos = {}

        # Check if there are any nf-core modules installed
        if (modules_dir / nf_core.modules.modules_repo.NF_CORE_MODULES_NAME).exists():
            repos[nf_core.modules.modules_repo.NF_CORE_MODULES_NAME] = (
                nf_core.modules.modules_repo.NF_CORE_MODULES_REMOTE,
                nf_core.modules.modules_repo.NF_CORE_MODULES_BASE_PATH,
            )

        # Check if there are any untracked repositories
        dirs_not_covered = self.dir_tree_uncovered(modules_dir, [Path(name) for name in repos])
        if len(dirs_not_covered) > 0:
            log.info("Found custom module repositories when creating 'modules.json'")
            # Loop until all directories in the base directory are covered by a remote
            while len(dirs_not_covered) > 0:
                log.info(
                    "The following director{s} in the modules directory are untracked: '{l}'".format(
                        s="ies" if len(dirs_not_covered) > 0 else "y",
                        l="', '".join(str(dir.relative_to(modules_dir)) for dir in dirs_not_covered),
                    )
                )
                nrepo_remote = questionary.text(
                    "Please provide a URL for for one of the repos contained in the untracked directories."
                ).unsafe_ask()
                # Verify that the remote exists
                while True:
                    try:
                        git.Git().ls_remote(nrepo_remote)
                        break
                    except git.exc.GitCommandError:
                        nrepo_remote = questionary.text(
                            "The provided remote does not seem to exist, please provide a new remote."
                        ).unsafe_ask()

                # Verify that there is a directory corresponding the remote
                nrepo_name = nf_core.modules.module_utils.path_from_remote(nrepo_remote)
                if not (modules_dir / nrepo_name).exists():
                    log.info(
                        "The provided remote does not seem to correspond to a local directory. "
                        "The directory structure should be the same as in the remote."
                    )
                    dir_name = questionary.text(
                        "Please provide the correct directory, it will be renamed. If left empty, the remote will be ignored."
                    ).unsafe_ask()
                    if dir_name:
                        (modules_dir, dir_name).rename(modules_dir / nrepo_name)
                    else:
                        continue

                # Prompt the user for the modules base path in the remote
                nrepo_base_path = questionary.text(
                    f"Please provide the path of the modules directory in the remote. "
                    f"Will default to '{nf_core.modules.modules_repo.NF_CORE_MODULES_BASE_PATH}' if left empty."
                ).unsafe_ask()
                if not nrepo_base_path:
                    nrepo_base_path = nf_core.modules.modules_repo.NF_CORE_MODULES_BASE_PATH

                repos[nrepo_name] = (nrepo_remote, nrepo_base_path)
                dirs_not_covered = self.dir_tree_uncovered(modules_dir, [Path(name) for name in repos])
        return repos

    def find_correct_commit_sha(self, module_name, module_path, modules_repo):
        """
        Returns the SHA for the latest commit where the local files are identical to the remote files
        Args:
            module_name (str): Name of module
            module_path (str): Path to module in local repo
            module_repo (str): Remote repo for module
        Returns:
            commit_sha (str): The latest commit SHA where local files are identical to remote files,
                              or None if no commit is found
        """
        # Find the correct commit SHA for the local module files.
        # We iterate over the commit history for the module until we find
        # a revision that matches the file contents
        commit_shas = (commit["git_sha"] for commit in modules_repo.get_module_git_log(module_name, depth=1000))
        for commit_sha in commit_shas:
            if all(modules_repo.module_files_identical(module_name, module_path, commit_sha).values()):
                return commit_sha
        return None

    def dir_tree_uncovered(self, modules_dir, repos):
        """
        Does a BFS of the modules directory to look for directories that
        are not tracked by a remote. The 'repos' argument contains the
        directories that are currently covered by remote, and it and its
        subdirectories are therefore ignore.

        Args:
            module_dir (Path): Base path of modules in pipeline
            repos ([ Path ]): List of repos that are covered by a remote

        Returns:
            dirs_not_covered ([ Path ]): A list of directories that are currently not covered by any remote.
        """

        # Initialise the FIFO queue. Note that we assume the directory to be correctly
        # configured, i.e. no files etc.
        fifo = [subdir for subdir in modules_dir.iterdir() if subdir.stem != "local"]
        depth = 1
        dirs_not_covered = []
        while len(fifo) > 0:
            temp_queue = []
            repos_at_level = {Path(*repo.parts[:depth]): len(repo.parts) for repo in repos}
            for dir in fifo:
                rel_dir = dir.relative_to(modules_dir)
                if rel_dir in repos_at_level.keys():
                    # Go the next depth if this directory is not one of the repos
                    if depth < repos_at_level[rel_dir]:
                        temp_queue.extend(dir.iterdir())
                else:
                    # Otherwise add the directory to the ones not covered
                    dirs_not_covered.append(dir)
            fifo = temp_queue
            depth += 1
        return dirs_not_covered

    def check_up_to_date(self):
        """
        Checks whether the modules installed in the directory
        are consistent with the entries in the 'modules.json' file and vice versa.

        If a module has an entry in the 'modules.json' file but is missing in the directory,
        we first try to reinstall the module from the remote and if that fails we remove the entry
        in 'modules.json'.

        If a module is installed but the entry in 'modules.json' is missing we iterate through
        the commit log in the remote to try to determine the SHA.
        """
        self.load()
        old_modules_json = copy.deepcopy(self.modules_json)

        # Compute the difference between the modules in the directory
        # and the modules in the 'modules.json' file
        # This is done by looking at all directories containing
        # a 'main.nf' file
        dirs = [
            os.path.relpath(dir_name, start=self.modules_dir)
            for dir_name, _, file_names in os.walk(self.modules_dir)
            if "main.nf" in file_names and not os.path.relpath(dir_name, start=self.modules_dir).startswith("local")
        ]

        missing_from_modules_json = []
        repo_names = list(old_modules_json["repos"].keys())
        for dir in dirs:
            # Check if the modules directory exists
            module_repo_name = None
            for repo in repo_names:
                if dir.startswith(repo + os.sep):
                    module_repo_name = repo
                    break
            if module_repo_name is not None:
                # If it does, check if the module is in the 'modules.json' file
                modules_path = os.path.relpath(dir, start=module_repo_name)

                if module_repo_name not in old_modules_json["repos"]:
                    missing_from_modules_json.append(dir)
                elif modules_path not in old_modules_json["repos"][module_repo_name].get("modules", {}):
                    missing_from_modules_json.append(dir)
                else:
                    old_modules_json["repos"][module_repo_name]["modules"].pop(modules_path)
                    if len(old_modules_json["repos"][module_repo_name]["modules"]) == 0:
                        old_modules_json["repos"].pop(module_repo_name)
            else:
                # If it is not, add it to the list of missing modules
                missing_from_modules_json.append(dir)

        # Check which repos are missing the remote url or base path
        for repo, values in old_modules_json.get("repos", {}).items():
            if "git_url" not in values or "base_path" not in values:
                raise UserWarning(
                    "The 'modules.json' file is not up to date. "
                    "Please reinstall it by removing it and rerunning the command."
                )
        # If there are any modules left in 'modules.json' after all installed are removed,
        # we try to reinstall them
        if len(old_modules_json["repos"]) > 0:
            missing_but_in_mod_json = [
                f"'{repo}/{module}'"
                for repo, contents in old_modules_json["repos"].items()
                for module in contents["modules"]
            ]
            log.info(
                f"Reinstalling modules found in 'modules.json' but missing from directory: {', '.join(missing_but_in_mod_json)}"
            )

            remove_from_mod_json = {}
            for repo, contents in old_modules_json["repos"].items():
                modules = contents["modules"]
                remote = contents["git_url"]
                base_path = contents["base_path"]

                modules_repo = nf_core.modules.modules_repo.ModulesRepo(remote_url=remote, base_path=base_path)
                install_dir = os.path.join(self.dir, "modules", modules_repo.fullname)

                for module, entry in modules.items():
                    sha = entry.get("git_sha")
                    if sha is None:
                        if repo not in remove_from_mod_json:
                            remove_from_mod_json[repo] = []
                        log.warning(
                            f"Could not find git SHA for module '{module}' in '{repo}' - removing from modules.json"
                        )
                        remove_from_mod_json[repo].append(module)
                        continue
                    if not modules_repo.install_module(module, install_dir, sha):
                        if repo not in remove_from_mod_json:
                            remove_from_mod_json[repo] = []
                        log.warning(f"Could not install module '{module}' in '{repo}' - removing from modules.json")
                        remove_from_mod_json[repo].append(module)
                        continue

            # If the reinstall fails, we remove those entries in 'modules.json'
            if sum(map(len, remove_from_mod_json.values())) > 0:
                uninstallable_mods = [
                    f"'{repo}/{module}'" for repo, modules in remove_from_mod_json.items() for module in modules
                ]
                if len(uninstallable_mods) == 1:
                    log.info(f"Was unable to reinstall {uninstallable_mods[0]}. Removing 'modules.json' entry")
                else:
                    log.info(
                        f"Was unable to reinstall some modules. Removing 'modules.json' entries: {', '.join(uninstallable_mods)}"
                    )

                for repo, modules in remove_from_mod_json.items():
                    for module in modules:
                        self.modules_json["repos"][repo]["modules"].pop(module)
                    if len(self.modules_json["repos"][repo]["modules"]) == 0:
                        self.modules_json["repos"].pop(repo)

        # If some modules didn't have an entry in the 'modules.json' file
        # we try to determine the SHA from the commit log of the remote
        dead_repos = []
        sb_local_repos = []
        if len(missing_from_modules_json) > 0:

            format_missing = [f"'{dir}'" for dir in missing_from_modules_json]
            if len(format_missing) == 1:
                log.info(f"Recomputing commit SHA for module {format_missing[0]} which was missing from 'modules.json'")
            else:
                log.info(
                    f"Recomputing commit SHAs for modules which were missing from 'modules.json': {', '.join(format_missing)}"
                )

            for dir in missing_from_modules_json:
                choice = questionary.select(
                    f"Found untracked file '{dir}'. Please select a choice",
                    choices=[
                        {"name": "Provide the remote", "value": 0},
                        {"name": "Move the directory to 'local'", "value": 1},
                        {"name": "Remove the files", "value": 2},
                    ],
                ).unsafe_ask()
                if choice == 0:
                    # Ask the user if the module belongs to an installed remote
                    choices = [{"name": "No", "value": (None, None)}] + [
                        {
                            "name": f"'{repo}' ({self.modules_json['repos'][repo]['git_url']})",
                            "value": (
                                self.modules_json["repos"][repo]["git_url"],
                                self.modules_json["repos"][repo]["base_path"],
                            ),
                        }
                        for repo in self.modules_json["repos"]
                    ]
                    remote, base_path = questionary.select(
                        "Does the module belong to an installed remote?",
                        choices=choices,
                        style=nf_core.utils.nfcore_question_style,
                    ).unsafe_ask()
                    if remote is None:
                        while True:
                            remote = questionary.text(
                                "Please provide the URL of the remote", style=nf_core.utils.nfcore_question_style
                            ).unsafe_ask()
                            # Verify that the name is consistent with the untracked file
                            repo = nf_core.modules.module_utils.path_from_remote(remote)
                            if not dir.startswith(repo):
                                log.info("The module name does not match the remote name")
                                continue
                            # Verify that the remote exists
                            try:
                                git.Git().ls_remote(remote)
                            except git.exc.GitCommandError:
                                log.info("The remote does not exist")
                                continue
                            # Ask the user for the modules base path in the remote
                            base_path = questionary.text(
                                f"Please provide the path of the modules directory in the remote. "
                                f"Will default to '{nf_core.modules.modules_repo.NF_CORE_MODULES_BASE_PATH}' if left empty."
                            ).unsafe_ask()
                            if not base_path:
                                base_path = nf_core.modules.modules_repo.NF_CORE_MODULES_BASE_PATH
                            break
                    else:
                        repo = nf_core.modules.module_utils.path_from_remote(remote)
                elif choice == 1:
                    sb_local_repos.append(repo)
                    continue
                else:
                    dead_repos.append(repo)
                    continue

                modules_repo = nf_core.modules.modules_repo.ModulesRepo(remote_url=remote, base_path=base_path)
                repo_path = os.path.join(self.dir, "modules", repo)
                module = os.path.relpath(dir, repo)
                module_path = os.path.join(repo_path, module)
                correct_commit_sha = self.find_correct_commit_sha(module, module_path, modules_repo)
                if correct_commit_sha is not None:
                    if repo not in self.modules_json["repos"]:
                        self.modules_json["repos"][repo] = {"git_url": remote, "base_path": base_path, "modules": {}}

                    self.modules_json["repos"][repo]["modules"][module] = {"git_sha": correct_commit_sha}
                else:
                    choices = [
                        {"name": "Move the directory to local", "value": 0},
                        {"name": "Remove the files", "value": 1},
                    ]
                    choice = questionary.select(f"Could not find commit SHA for {dir}", choices=choices).unsafe_ask()
                    if choice == 0:
                        sb_local_repos.append(repo)
                        continue
                    else:
                        dead_repos.append(repo)
                        continue

        # Remove the requested repos
        for repo in dead_repos:
            path = os.path.join(self.dir, "modules", repo)
            shutil.rmtree(path)

        # Copy the untracked repos to local
        for repo in sb_local_repos:
            modules_path = os.path.join(self.dir, "modules")
            path = os.path.join(modules_path, repo)
            local_path = os.path.join(modules_path, "local")

            # Create the local module directory if it doesn't already exist
            if not os.path.exists(local_path):
                os.makedirs(local_path)

            # Check if there is already a subdirectory with the name
            if os.path.exists(os.path.join(local_path, to_path)):
                to_path = path
                while os.path.exists(os.path.join(local_path, to_path)):
                    # Add a time suffix to the path to make it unique
                    # (do it again and again if it didn't work out...)
                    to_path += f"-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
                shutil.move(path, to_path)
                path = to_path

            shutil.move(path, local_path)

        self.dump()

    def load(self):
        """
        Loads the modules.json file into the variable 'modules_json'

        Sets the modules_json attribute to the loaded file.

        Raises:
            UserWarning: If the modules.json file is not found
        """
        modules_json_path = os.path.join(self.dir, "modules.json")
        try:
            with open(modules_json_path, "r") as fh:
                self.modules_json = json.load(fh)
        except FileNotFoundError:
            raise UserWarning("File 'modules.json' is missing")

    def update(self, modules_repo, module_name, module_version, write_file=True):
        """
        Updates the 'module.json' file with new module info

        Args:
            modules_repo (ModulesRepo): A ModulesRepo object configured for the new module
            module_name (str): Name of new module
            module_version (str): git SHA for the new module entry
            write_file (bool): whether to write the updated modules.json to a file.
        """
        if self.modules_json is None:
            self.load()
        repo_name = modules_repo.fullname
        remote_url = modules_repo.remote_url
        base_path = modules_repo.base_path
        branch = modules_repo.branch
        if repo_name not in self.modules_json["repos"]:
            self.modules_json["repos"][repo_name] = {"modules": {}, "git_url": remote_url, "base_path": base_path}
        repo_modules_entry = self.modules_json["repos"][repo_name]["modules"]
        if module_name not in repo_modules_entry:
            repo_modules_entry[module_name] = {}
        repo_modules_entry[module_name]["git_sha"] = module_version
        repo_modules_entry[module_name]["branch"] = branch

        # Sort the 'modules.json' repo entries
        self.modules_json["repos"] = nf_core.utils.sort_dictionary(self.modules_json["repos"])
        if write_file:
            self.dump()

    def remove_entry(self, module_name, repo_name):
        """
        Removes an entry from the 'modules.json' file.

        Args:
            module_name (str): Name of the module to be removed
            repo_name (str): Name of the repository containing the module
        Returns:
            (bool): True if the removal was successful, False otherwise
        """
        if not self.modules_json:
            return False
        if repo_name in self.modules_json.get("repos", {}):
            repo_entry = self.modules_json["repos"][repo_name]
            if module_name in repo_entry.get("modules", {}):
                repo_entry["modules"].pop(module_name)
            else:
                log.warning(f"Module '{repo_name}/{module_name}' is missing from 'modules.json' file.")
                return False
            if len(repo_entry["modules"]) == 0:
                self.modules_json["repos"].pop(repo_name)
        else:
            log.warning(f"Module '{repo_name}/{module_name}' is missing from 'modules.json' file.")
            return False

        self.dump()
        return True

    def add_patch_entry(self, module_name, repo_name, patch_filename, write_file=True):
        """
        Adds (or replaces) the patch entry for a module
        """
        if self.modules_json is None:
            self.load()
        if repo_name not in self.modules_json["repos"]:
            raise LookupError(f"Repo '{repo_name}' not present in 'modules.json'")
        if module_name not in self.modules_json["repos"][repo_name]["modules"]:
            raise LookupError(f"Module '{repo_name}/{module_name}' not present in 'modules.json'")
        self.modules_json["repos"][repo_name]["modules"][module_name]["patch"] = str(patch_filename)
        if write_file:
            self.dump()

    def get_patch_fn(self, module_name, repo_name):
        """
        Get the patch filename of a module

        Args:
            module_name (str): The name of the module
            repo_name (str): The name of the repository containing the module

        Returns:
            (str): The patch filename for the module, None if not present
        """
        if self.modules_json is None:
            self.load()
        path = self.modules_json["repos"].get(repo_name, {}).get("modules").get(module_name, {}).get("patch")
        return Path(path) if path is not None else None

    def repo_present(self, repo_name):
        """
        Checks if a repo is present in the modules.json file
        Args:
            repo_name (str): Name of the repository
        Returns:
            (bool): Whether the repo exists in the modules.json
        """
        if self.modules_json is None:
            self.load()
        return repo_name in self.modules_json.get("repos", {})

    def module_present(self, module_name, repo_name):
        """
        Checks if a module is present in the modules.json file
        Args:
            module_name (str): Name of the module
            repo_name (str): Name of the repository
        Returns:
            (bool): Whether the module is present in the 'modules.json' file
        """
        if self.modules_json is None:
            self.load()
        return module_name in self.modules_json.get("repos", {}).get(repo_name, {}).get("modules", {})

    def get_modules_json(self):
        """
        Returns a copy of the loaded modules.json

        Returns:
            (dict): A copy of the loaded modules.json
        """
        if self.modules_json is None:
            self.load()
        return copy.deepcopy(self.modules_json)

    def get_module_version(self, module_name, repo_name):
        """
        Returns the version of a module

        Args:
            module_name (str): Name of the module
            repo_name (str): Name of the repository

        Returns:
            (str): The git SHA of the module if it exists, None otherwise
        """
        if self.modules_json is None:
            self.load()
        return (
            self.modules_json.get("repos", {})
            .get(repo_name, {})
            .get("modules", {})
            .get(module_name, {})
            .get("git_sha", None)
        )

    def get_git_url(self, repo_name):
        """
        Returns the git url of a repo

        Args:
            repo_name (str): Name of the repository

        Returns:
            (str): The git url of the repository if it exists, None otherwise
        """
        if self.modules_json is None:
            self.load()
        return self.modules_json.get("repos", {}).get(repo_name, {}).get("git_url", None)

    def get_base_path(self, repo_name):
        """
        Returns the modules base path of a repo
        Args:
            repo_name (str): Name of the repository

        Returns:
            (str): The base path of the repository if it exists, None otherwise
        """
        if self.modules_json is None:
            self.load()
        return self.modules_json.get("repos", {}).get(repo_name, {}).get("base_path", None)

    def get_all_modules(self):
        """
        Retrieves all pipeline modules that are reported in the modules.json

        Returns:
            (dict[str, [str]]): Dictionary indexed with the repo names, with a
                                list of modules as values
        """
        if self.modules_json is None:
            self.load()
        if self.pipeline_modules is None:
            self.pipeline_modules = {}
            for repo, repo_entry in self.modules_json.get("repos", {}).items():
                if "modules" in repo_entry:
                    self.pipeline_modules[repo] = list(repo_entry["modules"])

        return self.pipeline_modules

    def get_module_branch(self, module, repo_name):
        """
        Gets the branch from which the module was installed

        Returns:
            (str): The branch name
        Raises:
            LookupError: If their is no branch entry in the `modules.json`
        """
        if self.modules_json is None:
            self.load()
        branch = self.modules_json["repos"].get(repo_name, {}).get("modules", {}).get(module, {}).get("branch")
        if branch is None:
            raise LookupError(
                f"Could not find branch information for module '{Path(repo_name, module)}'."
                f"Please remove the 'modules.json' and rerun the command to recreate it"
            )
        return branch

    def dump(self):
        """
        Sort the modules.json, and write it to file
        """
        # Sort the modules.json
        self.modules_json["repos"] = nf_core.utils.sort_dictionary(self.modules_json["repos"])
        modules_json_path = os.path.join(self.dir, "modules.json")
        with open(modules_json_path, "w") as fh:
            json.dump(self.modules_json, fh, indent=4)
            fh.write("\n")
