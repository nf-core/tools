import copy
import datetime
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

import git
import questionary
from git.exc import GitCommandError

import nf_core.modules.module_utils
import nf_core.modules.modules_repo
import nf_core.utils

from .modules_differ import ModulesDiffer

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
        self.modules_dir = Path(self.dir, "modules")
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
        modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "repos": {}}
        modules_dir = Path(self.dir, "modules")

        if not modules_dir.exists():
            raise UserWarning("Can't find a ./modules directory. Is this a DSL2 pipeline?")

        repos, _ = self.get_pipeline_module_repositories(modules_dir)

        # Get all module names in the repos
        repo_module_names = [
            (
                repo_name,
                [
                    str(Path(dir_name).relative_to(modules_dir / repo_name))
                    for dir_name, _, file_names in os.walk(modules_dir / repo_name)
                    if "main.nf" in file_names
                ],
                repo_remote,
            )
            for repo_name, repo_remote in repos.items()
        ]

        for repo_name, module_names, remote_url in sorted(repo_module_names):
            modules_json["repos"][repo_name] = {}
            modules_json["repos"][repo_name]["git_url"] = remote_url
            modules_json["repos"][repo_name]["modules"] = {}
            modules_json["repos"][repo_name]["modules"] = self.determine_module_branches_and_shas(
                repo_name, remote_url, module_names
            )
        # write the modules.json file and assign it to the object
        modules_json_path = Path(self.dir, "modules.json")
        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=4)
            fh.write("\n")
        self.modules_json = modules_json

    def get_pipeline_module_repositories(self, modules_dir, repos=None):
        """
        Finds all module repositories in the modules directory.
        Ignores the local modules.

        Args:
            modules_dir (Path): base directory for the module files
        Returns
            repos ([ (str, str, str) ]),
            renamed_dirs (dict[Path, Path]): List of tuples of repo name, repo
                                             remote URL and path to modules in
                                             repo
        """
        if repos is None:
            repos = {}

        # Check if there are any nf-core modules installed
        if (modules_dir / nf_core.modules.modules_repo.NF_CORE_MODULES_NAME).exists():
            repos[
                nf_core.modules.modules_repo.NF_CORE_MODULES_NAME
            ] = nf_core.modules.modules_repo.NF_CORE_MODULES_REMOTE
        # The function might rename some directories, keep track of them
        renamed_dirs = {}
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
                    "Please provide a URL for for one of the repos contained in the untracked directories.",
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()
                # Verify that the remote exists
                while True:
                    try:
                        git.Git().ls_remote(nrepo_remote)
                        break
                    except GitCommandError:
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
                        "Please provide the correct directory, it will be renamed. If left empty, the remote will be ignored.",
                        style=nf_core.utils.nfcore_question_style,
                    ).unsafe_ask()
                    if dir_name:
                        old_path = modules_dir / dir_name
                        new_path = modules_dir / nrepo_name
                        old_path.rename(new_path)
                        renamed_dirs[old_path] = new_path
                    else:
                        continue

                repos[nrepo_name] = (nrepo_remote, "modules")
                dirs_not_covered = self.dir_tree_uncovered(modules_dir, [Path(name) for name in repos])
        return repos, renamed_dirs

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
            for directory in fifo:
                rel_dir = directory.relative_to(modules_dir)
                if rel_dir in repos_at_level.keys():
                    # Go the next depth if this directory is not one of the repos
                    if depth < repos_at_level[rel_dir]:
                        temp_queue.extend(directory.iterdir())
                else:
                    # Otherwise add the directory to the ones not covered
                    dirs_not_covered.append(directory)
            fifo = temp_queue
            depth += 1
        return dirs_not_covered

    def determine_module_branches_and_shas(self, repo_name, remote_url, modules):
        """
        Determines what branch and commit sha each module in the pipeline belong to

        Assumes all modules are installed from the default branch. If it fails to find the
        module in the default branch, it prompts the user with the available branches

        Args:
            repo_name (str): The name of the module repository
            remote_url (str): The url to the remote repository
            modules ([str]): List of names of installed modules from the repository

        Returns:
            (dict[str, dict[str, str]]): The module.json entries for the modules
                                         from the repository
        """
        default_modules_repo = nf_core.modules.modules_repo.ModulesRepo(remote_url=remote_url)
        repo_path = self.modules_dir / repo_name
        # Get the branches present in the repository, as well as the default branch
        available_branches = nf_core.modules.modules_repo.ModulesRepo.get_remote_branches(remote_url)
        sb_local = []
        dead_modules = []
        repo_entry = {}
        for module in sorted(modules):
            modules_repo = default_modules_repo
            module_path = repo_path / module
            correct_commit_sha = None
            tried_branches = {default_modules_repo.branch}
            found_sha = False
            while True:
                # If the module is patched
                patch_file = module_path / f"{module}.diff"
                if patch_file.is_file():
                    temp_module_dir = self.try_apply_patch_reverse(module, repo_name, patch_file, module_path)
                    correct_commit_sha = self.find_correct_commit_sha(module, temp_module_dir, modules_repo)
                else:
                    correct_commit_sha = self.find_correct_commit_sha(module, module_path, modules_repo)
                if correct_commit_sha is None:
                    log.info(f"Was unable to find matching module files in the {modules_repo.branch} branch.")
                    choices = [{"name": "No", "value": None}] + [
                        {"name": branch, "value": branch} for branch in (available_branches - tried_branches)
                    ]
                    branch = questionary.select(
                        "Was the modules installed from a different branch in the remote?",
                        choices=choices,
                        style=nf_core.utils.nfcore_question_style,
                    ).unsafe_ask()
                    if branch is None:
                        action = questionary.select(
                            f"Module is untracked '{module}'. Please select what action to take",
                            choices=[
                                {"name": "Move the directory to 'local'", "value": 0},
                                {"name": "Remove the files", "value": 1},
                            ],
                            style=nf_core.utils.nfcore_question_style,
                        ).unsafe_ask()
                        if action == 0:
                            sb_local.append(module)
                        else:
                            dead_modules.append(module)
                        break
                    # Create a new modules repo with the selected branch, and retry find the sha
                    modules_repo = nf_core.modules.modules_repo.ModulesRepo(
                        remote_url=remote_url, branch=branch, no_pull=True, hide_progress=True
                    )
                else:
                    found_sha = True
                    break
            if found_sha:
                repo_entry[module] = {"branch": modules_repo.branch, "git_sha": correct_commit_sha}

        # Clean up the modules we were unable to find the sha for
        for module in sb_local:
            log.debug(f"Moving module '{Path(repo_name, module)}' to 'local' directory")
            self.move_module_to_local(module, repo_name)

        for module in dead_modules:
            log.debug(f"Removing module {Path(repo_name, module)}'")
            shutil.rmtree(repo_path / module)

        return repo_entry

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

    def move_module_to_local(self, module, repo_name):
        """
        Move a module to the 'local' directory

        Args:
            module (str): The name of the modules
            repo_name (str): The name of the repository the module resides in
        """
        current_path = self.modules_dir / repo_name / module
        local_modules_dir = self.modules_dir / "local"
        if not local_modules_dir.exists():
            local_modules_dir.mkdir()

        to_name = module
        # Check if there is already a subdirectory with the name
        while (local_modules_dir / to_name).exists():
            # Add a time suffix to the path to make it unique
            # (do it again and again if it didn't work out...)
            to_name += f"-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
        shutil.move(current_path, local_modules_dir / to_name)

    def unsynced_modules(self):
        """
        Compute the difference between the modules in the directory and the
        modules in the 'modules.json' file. This is done by looking at all
        directories containing a 'main.nf' file

        Returns:
            (untrack_dirs ([ Path ]), missing_installation (dict)): Directories that are not tracked
            by the modules.json file, and modules in the modules.json where
            the installation directory is missing
        """
        missing_installation = copy.deepcopy(self.modules_json["repos"])
        dirs = [
            Path(dir_name).relative_to(self.modules_dir)
            for dir_name, _, file_names in os.walk(self.modules_dir)
            if "main.nf" in file_names and not str(Path(dir_name).relative_to(self.modules_dir)).startswith("local")
        ]
        untracked_dirs = []
        for dir in dirs:
            # Check if the modules directory exists
            module_repo_name = None
            for repo in missing_installation:
                if str(dir).startswith(repo + os.sep):
                    module_repo_name = repo
                    break
            if module_repo_name is not None:
                # If it does, check if the module is in the 'modules.json' file
                module = str(dir.relative_to(module_repo_name))
                module_repo = missing_installation[module_repo_name]

                if module not in module_repo.get("modules", {}):
                    untracked_dirs.append(dir)
                else:
                    # Check if the entry has a git sha and branch before removing
                    modules = module_repo["modules"]
                    if "git_sha" not in modules[module] or "branch" not in modules[module]:
                        self.determine_module_branches_and_shas(
                            module, module_repo["git_url"], module_repo["base_path"], [module]
                        )
                    module_repo["modules"].pop(module)
                    if len(module_repo["modules"]) == 0:
                        missing_installation.pop(module_repo_name)
            else:
                # If it is not, add it to the list of missing modules
                untracked_dirs.append(dir)

        return untracked_dirs, missing_installation

    def has_git_url_and_modules(self):
        """
        Check that all repo entries in the modules.json
        has a git url and a modules dict entry
        Returns:
            (bool): True if they are found for all repos, False otherwise
        """
        for repo_entry in self.modules_json.get("repos", {}).values():
            if "git_url" not in repo_entry or "modules" not in repo_entry:
                log.warning(f"modules.json entry {repo_entry} does not have a git_url or modules entry")
                return False
            elif (
                not isinstance(repo_entry["git_url"], str)
                or repo_entry["git_url"] == ""
                or not isinstance(repo_entry["modules"], dict)
                or repo_entry["modules"] == {}
            ):
                log.warning(f"modules.json entry {repo_entry} has non-string or empty entries for git_url or modules")
                return False
        return True

    def reinstall_repo(self, repo_name, remote_url, module_entries):
        """
        Reinstall modules from a repository

        Args:
            repo_name (str): The name of the repository
            remote_url (str): The git url of the remote repository
            modules ([ dict[str, dict[str, str]] ]): Module entries with
            branch and git sha info

        Returns:
            ([ str ]): List of modules that we failed to install
        """
        branches_and_mods = {}
        failed_to_install = []
        for module, module_entry in module_entries.items():
            if "git_sha" not in module_entry or "branch" not in module_entry:
                failed_to_install.append(module)
            else:
                branch = module_entry["branch"]
                sha = module_entry["git_sha"]
                if branch not in branches_and_mods:
                    branches_and_mods[branch] = []
                branches_and_mods[branch].append((module, sha))

        for branch, modules in branches_and_mods.items():
            try:
                modules_repo = nf_core.modules.modules_repo.ModulesRepo(remote_url=remote_url, branch=branch)
            except LookupError as e:
                log.error(e)
                failed_to_install.extend(modules)
            for module, sha in modules:
                if not modules_repo.install_module(module, (self.modules_dir / repo_name), sha):
                    log.warning(f"Could not install module '{Path(repo_name, module)}' - removing from modules.json")
                    failed_to_install.append(module)
        return failed_to_install

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
        try:
            self.load()
            if not self.has_git_url_and_modules():
                raise UserWarning
        except UserWarning:
            log.info("The 'modules.json' file is not up to date. Recreating the 'module.json' file.")
            self.create()

        missing_from_modules_json, missing_installation = self.unsynced_modules()

        # If there are any modules left in 'modules.json' after all installed are removed,
        # we try to reinstall them
        if len(missing_installation) > 0:
            missing_but_in_mod_json = [
                f"'{repo}/{module}'"
                for repo, contents in missing_installation.items()
                for module in contents["modules"]
            ]
            log.info(
                f"Reinstalling modules found in 'modules.json' but missing from directory: {', '.join(missing_but_in_mod_json)}"
            )

            remove_from_mod_json = {}
            for repo, contents in missing_installation.items():
                module_entries = contents["modules"]
                remote_url = contents["git_url"]
                remove_from_mod_json[repo] = self.reinstall_repo(repo, remote_url, module_entries)

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

                for repo, module_entries in remove_from_mod_json.items():
                    for module in module_entries:
                        self.modules_json["repos"][repo]["modules"].pop(module)
                    if len(self.modules_json["repos"][repo]["modules"]) == 0:
                        self.modules_json["repos"].pop(repo)

        # If some modules didn't have an entry in the 'modules.json' file
        # we try to determine the SHA from the commit log of the remote
        if len(missing_from_modules_json) > 0:
            format_missing = [f"'{dir}'" for dir in missing_from_modules_json]
            if len(format_missing) == 1:
                log.info(f"Recomputing commit SHA for module {format_missing[0]} which was missing from 'modules.json'")
            else:
                log.info(
                    f"Recomputing commit SHAs for modules which were missing from 'modules.json': {', '.join(format_missing)}"
                )

            # Get the remotes we are missing
            tracked_repos = {
                repo_name: (repo_entry["git_url"]) for repo_name, repo_entry in self.modules_json["repos"].items()
            }
            repos, _ = self.get_pipeline_module_repositories(self.modules_dir, tracked_repos)

            modules_with_repos = (
                (repo_name, str(dir.relative_to(repo_name)))
                for dir in missing_from_modules_json
                for repo_name in repos
                if nf_core.utils.is_relative_to(dir, repo_name)
            )

            repos_with_modules = {}
            for repo_name, module in modules_with_repos:
                if repo_name not in repos_with_modules:
                    repos_with_modules[repo_name] = []
                repos_with_modules[repo_name].append(module)

            for repo_name, modules in repos_with_modules.items():
                remote_url = repos[repo_name]
                repo_entry = self.determine_module_branches_and_shas(repo_name, remote_url, modules)
                if repo_name in self.modules_json["repos"]:
                    self.modules_json["repos"][repo_name]["modules"].update(repo_entry)
                else:
                    self.modules_json["repos"][repo_name] = {
                        "git_url": remote_url,
                        "modules": repo_entry,
                    }

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
        branch = modules_repo.branch
        if repo_name not in self.modules_json["repos"]:
            self.modules_json["repos"][repo_name] = {"modules": {}, "git_url": remote_url}
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

    def try_apply_patch_reverse(self, module, repo_name, patch_relpath, module_dir):
        """
        Try reverse applying a patch file to the modified module files

        Args:
            module (str): The name of the module
            repo_name (str): The name of the repository where the module resides
            patch_relpath (Path | str): The path to patch file in the pipeline
            module_dir (Path | str): The module directory in the pipeline

        Returns:
            (Path | str): The path of the folder where the module patched files are

        Raises:
            LookupError: If patch was not applied
        """
        module_fullname = str(Path(repo_name, module))
        patch_path = Path(self.dir / patch_relpath)

        try:
            new_files = ModulesDiffer.try_apply_patch(module, repo_name, patch_path, module_dir, reverse=True)
        except LookupError as e:
            raise LookupError(f"Failed to apply patch in reverse for module '{module_fullname}' due to: {e}")

        # Write the patched files to a temporary directory
        log.debug("Writing patched files to tmpdir")
        temp_dir = Path(tempfile.mkdtemp())
        temp_module_dir = temp_dir / module
        temp_module_dir.mkdir(parents=True, exist_ok=True)
        for file, new_content in new_files.items():
            fn = temp_module_dir / file
            with open(fn, "w") as fh:
                fh.writelines(new_content)

        return temp_module_dir

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

    def __str__(self):
        if self.modules_json is None:
            self.load()
        return json.dumps(self.modules_json, indent=4)

    def __repr__(self):
        return self.__str__()
