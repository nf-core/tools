import json
import logging
import os

import git
import questionary
import rich.progress

import nf_core.modules.module_utils
import nf_core.utils
from nf_core.modules.modules_repo import (
    NF_CORE_MODULES_BASE_PATH,
    NF_CORE_MODULES_NAME,
    NF_CORE_MODULES_REMOTE,
    ModulesRepo,
)

log = logging.getLogger(__name__)


class ModulesJson:
    def __init__(self, pipeline_dir):
        self.dir = pipeline_dir
        self.modules_json = None

    def create_modules_json(self):
        """
        Creates the modules.json file from the modules installed in the pipeline directory
        """
        pipeline_config = nf_core.utils.fetch_wf_config(self.dir)
        pipeline_name = pipeline_config.get("manifest.name", "")
        pipeline_url = pipeline_config.get("manifest.homePage", "")
        modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "repos": dict()}
        modules_dir = f"{self.dir}/modules"

        if not os.path.exists(modules_dir):
            raise UserWarning("Can't find a ./modules directory. Is this a DSL2 pipeline?")

        repos = self.get_pipeline_module_repositories(modules_dir)

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
            for repo_name, repo_remote, base_path in repos
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
                    modules_repo = ModulesRepo(remote_url=remote, base_path=base_path, no_progress=True)
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

    def get_pipeline_module_repositories(self, modules_dir):
        """
        Finds all module repositories in the modules directory. Ignores the local modules.
        Args:
            modules_dir (str): base directory for the module files
        Returns
            repos [ (str, str, str) ]: List of tuples of repo name, repo remote URL and path to modules in repo
        """
        # Check if there are any nf-core modules installed
        if os.path.exists(os.path.join(modules_dir, NF_CORE_MODULES_NAME)):
            repos = [(NF_CORE_MODULES_NAME, NF_CORE_MODULES_REMOTE, NF_CORE_MODULES_BASE_PATH)]
        else:
            repos = []
        # Check if there are any untracked repositories
        dirs_not_covered = self.dir_tree_uncovered(modules_dir, [name for name, _, _ in repos])
        if len(dirs_not_covered) > 0:
            log.info("Found custom module repositories when creating 'modules.json'")
            # Loop until all directories in the base directory are covered by a remote
            while len(dirs_not_covered) > 0:
                log.info(
                    "The following director{s} in the modules directory are untracked: '{l}'".format(
                        s="ies" if len(dirs_not_covered) > 0 else "y", l="', '".join(dirs_not_covered)
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
                if not os.path.exists(os.path.join(modules_dir, nrepo_name)):
                    log.info(
                        "The provided remote does not seem to correspond to a local directory. "
                        "The directory structure should be the same as in the remote."
                    )
                    dir_name = questionary.text(
                        "Please provide the correct directory, it will be renamed. If left empty, the remote will be ignored."
                    ).unsafe_ask()
                    if dir_name:
                        os.rename(os.path.join(modules_dir, dir_name), os.path.join(modules_dir, nrepo_name))
                    else:
                        continue

                # Prompt the user for the modules base path in the remote
                nrepo_base_path = questionary.text(
                    f"Please provide the path of the modules directory in the remote. "
                    f"Will default to '{NF_CORE_MODULES_BASE_PATH}' if left empty."
                ).unsafe_ask()
                if not nrepo_base_path:
                    nrepo_base_path = NF_CORE_MODULES_BASE_PATH

                repos.append((nrepo_name, nrepo_remote, nrepo_base_path))
                dirs_not_covered = self.dir_tree_uncovered(modules_dir, [name for name, _, _ in repos])
        return repos

    def find_correct_commit_sha(self, module_name, module_path, modules_repo):
        """
        Returns the SHA for the latest commit where the local files are identical to the remote files
        Args:
            module_name (str): Name of module
            module_path (str): Path to module in local repo
            module_repo (str): Remote repo for module
        Returns:
            commit_sha (str): The latest commit SHA where local files are identical to remote files
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
        Does a BFS of the modules directory of a pipeline and rapports any directories
        that are not found in the list of repos
        """
        # Initialise the FIFO queue. Note that we assume the directory to be correctly
        # configured, i.e. no files etc.
        fifo = [os.path.join(modules_dir, subdir) for subdir in os.listdir(modules_dir) if subdir != "local"]
        depth = 1
        dirs_not_covered = []
        while len(fifo) > 0:
            temp_queue = []
            repos_at_level = {os.path.join(*os.path.split(repo)[:depth]): len(os.path.split(repo)) for repo in repos}
            for dir in fifo:
                rel_dir = os.path.relpath(dir, modules_dir)
                if rel_dir in repos_at_level.keys():
                    # Go the next depth if this directory is not one of the repos
                    if depth < repos_at_level[rel_dir]:
                        temp_queue.extend([os.path.join(dir, subdir) for subdir in os.listdir(dir)])
                else:
                    # Otherwise add the directory to the ones not covered
                    dirs_not_covered.append(dir)
            fifo = temp_queue
            depth += 1
        return dirs_not_covered

    def load_modules_json(self):
        """
        Loads the modules.json file into the variable 'modules_json'
        """
        modules_json_path = os.path.join(self.dir, "modules.json")
        try:
            with open(modules_json_path, "r") as fh:
                modules_json = json.load(fh)
        except FileNotFoundError:
            log.error("File 'modules.json' is missing")
            modules_json = None
        self.modules_json = modules_json

    def update_modules_json(self, modules_json, modules_repo, module_name, module_version, write_file=True):
        """
        Updates the 'module.json' file with new module info
        """
        repo_name = modules_repo.fullname
        remote_url = modules_repo.remote_url
        base_path = modules_repo.base_path
        if repo_name not in modules_json["repos"]:
            modules_json["repos"][repo_name] = {"modules": {}, "git_url": remote_url, "base_path": base_path}
        modules_json["repos"][repo_name]["modules"][module_name] = {"git_sha": module_version}
        # Sort the 'modules.json' repo entries
        modules_json["repos"] = nf_core.utils.sort_dictionary(modules_json["repos"])
        if write_file:
            self.dump_modules_json(modules_json)
        else:
            return modules_json

    def remove_modules_json_entry(self, module, repo_name):

        if not self.modules_json:
            return False
        if repo_name in self.modules_json.get("repos", {}):
            repo_entry = self.modules_json["repos"][repo_name]
            if module in repo_entry.get("modules", {}):
                repo_entry["modules"].pop(module)
            else:
                log.warning(f"Module '{repo_name}/{module}' is missing from 'modules.json' file.")
                return False
            if len(repo_entry) == 0:
                self.modules_json["repos"].pop(repo_name)
        else:
            log.warning(f"Module '{repo_name}/{module}' is missing from 'modules.json' file.")
            return False

        self.dump_modules_json()

        return True

    def repo_present(self, repo_name):
        """
        Checks if a repo is present in the modules.json file
        """
        return repo_name in self.modules_json.get("repos", {})

    def module_present(self, module_name, repo_name):
        """
        Checks if a module is present in the modules.json file
        """
        return module_name in self.modules_json.get("repos", {}).get(repo_name, {}).get("modules", {})

    def dump_modules_json(self):
        """Build filename for modules.json and write to file."""
        modules_json_path = os.path.join(self.dir, "modules.json")
        with open(modules_json_path, "w") as fh:
            json.dump(self.modules_json, fh, indent=4)
            fh.write("\n")
