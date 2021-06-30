import glob
import json
import os
import requests
import sys
import logging
import questionary
import rich
import datetime
from itertools import count

from requests import api

import nf_core.utils

from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


def get_module_git_log(module_name, per_page=30, page_nbr=1, since="2020-11-25T00:00:00Z"):
    """
    Fetches the commit history the of requested module
    Args:
        module_name (str): Name of module
        per_page (int): Number of commits per page returned by API
        page_nbr (int): Page number of the retrieved commits
        since (str): Only show commits later than this timestamp.
        Time should be given in ISO-8601 format: YYYY-MM-DDTHH:MM:SSZ.

    Returns:
        [ dict ]: List of commit SHAs and associated (truncated) message
    """
    api_url = f"https://api.github.com/repos/nf-core/modules/commits?sha=master&path=software/{module_name}&per_page={per_page}&page={page_nbr}&since={since}"
    log.debug(f"Fetching commit history of module '{module_name}' from github API")
    response = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
    if response.status_code == 200:
        commits = response.json()

        if len(commits) == 0:
            log.debug(f"Reached end of commit history for '{module_name}'")
            return []
        else:
            # Return the commit SHAs and the first line of the commit message
            return [
                {"git_sha": commit["sha"], "trunc_message": commit["commit"]["message"].partition("\n")[0]}
                for commit in commits
            ]
    elif response.status_code == 404:
        log.error(f"Module '{module_name}' not found in 'nf-core/modules/'\n{api_url}")
        sys.exit(1)
    else:
        raise SystemError(f"Unable to fetch commit SHA for module {module_name}")


def get_commit_info(commit_sha):
    """
    Fetches metadata about the commit (dates, message, etc.)
    Args:
        module_name (str): Name of module
        commit_sha (str): The SHA of the requested commit
    Returns:
        message (str): The commit message for the requested commit
        date (str): The commit date for the requested commit
    Raises:
        LookupError: If the call to the API fails.
    """
    api_url = f"https://api.github.com/repos/nf-core/modules/commits/{commit_sha}?stats=false"
    log.debug(f"Fetching commit metadata for commit at {commit_sha}")
    response = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
    if response.status_code == 200:
        commit = response.json()
        message = commit["commit"]["message"].partition("\n")[0]
        raw_date = commit["commit"]["author"]["date"]

        # Parse the date returned from the API
        date_obj = datetime.datetime.strptime(raw_date, "%Y-%m-%dT%H:%M:%SZ")
        date = str(date_obj.date())

        return message, date
    elif response.status_code == 404:
        raise LookupError(f"Commit '{commit_sha}' not found in 'nf-core/modules/'\n{api_url}")
    else:
        raise LookupError(f"Unable to fetch metadata for commit SHA {commit_sha}")


def create_modules_json(pipeline_dir):
    """
    Create the modules.json files

    Args:
        pipeline_dir (str): The directory where the `modules.json` should be created
    """
    pipeline_config = nf_core.utils.fetch_wf_config(pipeline_dir)
    pipeline_name = pipeline_config["manifest.name"]
    pipeline_url = pipeline_config["manifest.homePage"]
    modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "modules": {}}
    all_module_file_paths = glob.glob(f"{pipeline_dir}/modules/nf-core/software/**/*", recursive=True)

    # Extract the module paths from the file paths
    module_paths = list(set(map(os.path.dirname, filter(os.path.isfile, all_module_file_paths))))
    module_names = [path.replace(f"{pipeline_dir}/modules/nf-core/software/", "") for path in module_paths]
    module_repo = ModulesRepo()
    progress_bar = rich.progress.Progress(
        "[bold blue]{task.description}",
        rich.progress.BarColumn(bar_width=None),
        "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
        transient=True,
    )
    with progress_bar:
        file_progress = progress_bar.add_task(
            "Creating 'modules.json' file", total=len(module_names), test_name="module.json"
        )
        for module_name, module_path in zip(module_names, module_paths):
            progress_bar.update(file_progress, advance=1, test_name=module_name)
            try:
                # Find the correct commit SHA for the local files.
                # We iterate over the commit log pages until we either
                # find a matching commit or we reach the end of the commits
                correct_commit_sha = None
                commit_page_nbr = 1
                while correct_commit_sha is None:

                    commit_shas = [
                        commit["git_sha"] for commit in get_module_git_log(module_name, page_nbr=commit_page_nbr)
                    ]
                    correct_commit_sha = find_correct_commit_sha(module_name, module_path, module_repo, commit_shas)
                    commit_page_nbr += 1

                modules_json["modules"][module_name] = {"git_sha": correct_commit_sha}
            except SystemError as e:
                log.error(e)
                log.error("Will not create 'modules.json' file")
                sys.exit(1)
    modules_json_path = os.path.join(pipeline_dir, "modules.json")
    with open(modules_json_path, "w") as fh:
        json.dump(modules_json, fh, indent=4)


def find_correct_commit_sha(module_name, module_path, modules_repo, commit_shas):
    """
    Returns the SHA for the latest commit where the local files are identical to the remote files
    Args:
        module_name (str): Name of module
        module_path (str): Path to module in local repo
        module_repo (str): Remote repo for module
        commit_shas ([ str ]): List of commit SHAs for module, sorted in descending order
    Returns:
        commit_sha (str): The latest commit SHA where local files are identical to remote files
    """

    files_to_check = ["main.nf", "functions.nf", "meta.yml"]
    local_file_contents = [None, None, None]
    for i, file in enumerate(files_to_check):
        try:
            local_file_contents[i] = open(os.path.join(module_path, file), "r").read()
        except FileNotFoundError as e:
            log.debug(f"Could not open file: {os.path.join(module_path, file)}")
            continue
    for commit_sha in commit_shas:
        if local_module_equal_to_commit(local_file_contents, module_name, modules_repo, commit_sha):
            return commit_sha
    return None


def local_module_equal_to_commit(local_files, module_name, modules_repo, commit_sha):
    """
    Compares the local module files to the module files for the given commit sha
    Args:
        local_files ([ str ]): Contents of local files. `None` if files doesn't exist
        module_name (str): Name of module
        module_repo (str): Remote repo for module
        commit_sha (str): Commit SHA for remote version to compare against local version
    Returns:
        bool: Whether all local files are identical to remote version
    """

    files_to_check = ["main.nf", "functions.nf", "meta.yml"]
    files_are_equal = [False, False, False]
    remote_copies = [None, None, None]

    module_base_url = f"https://raw.githubusercontent.com/{modules_repo.name}/{commit_sha}/software/{module_name}"
    for i, file in enumerate(files_to_check):
        # Download remote copy and compare
        api_url = f"{module_base_url}/{file}"
        r = requests.get(url=api_url)
        if r.status_code != 200:
            log.debug(f"Could not download remote copy of file module {module_name}/{file}")
            log.debug(api_url)
        else:
            try:
                remote_copies[i] = r.content.decode("utf-8")
            except UnicodeDecodeError as e:
                log.debug(f"Could not decode remote copy of {file} for the {module_name} module")

        # Compare the contents of the files.
        # If the file is missing from both the local and remote repo
        # we will get the comparision None == None
        if local_files[i] == remote_copies[i]:
            files_are_equal[i] = True

    return all(files_are_equal)


def get_repo_type(dir):
    """
    Determine whether this is a pipeline repository or a clone of
    nf-core/modules
    """
    # Verify that the pipeline dir exists
    if dir is None or not os.path.exists(dir):
        log.error("Could not find directory: {}".format(dir))
        sys.exit(1)

    # Determine repository type
    if os.path.exists(os.path.join(dir, "main.nf")):
        return "pipeline"
    elif os.path.exists(os.path.join(dir, "software")):
        return "modules"
    else:
        log.error("Could not determine repository type of {}".format(dir))
        sys.exit(1)
