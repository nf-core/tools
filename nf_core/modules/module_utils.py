import glob
import json
import os
import requests
import logging
import rich
import datetime


import nf_core.utils

from .modules_repo import ModulesRepo
from .nfcore_module import NFCoreModule

log = logging.getLogger(__name__)


class ModuleException(Exception):
    """Exception raised when there was an error with module commands"""

    pass


def module_exist_in_repo(module_name, modules_repo):
    """
    Checks whether a module exists in a branch of a GitHub repository

    Args:
        module_name (str): Name of module
        modules_repo (ModulesRepo): A ModulesRepo object configured for the repository in question
    Returns:
        boolean: Whether the module exist in the repo or not.
    """
    api_url = (
        f"https://api.github.com/repos/{modules_repo.name}/contents/modules/{module_name}?ref={modules_repo.branch}"
    )
    response = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
    return not (response.status_code == 404)


def get_module_git_log(
    module_name, owner="nf-core", modules_repo=None, per_page=30, page_nbr=1, since="2021-07-07T00:00:00Z"
):
    """
    Fetches the commit history the of requested module since a given date. The default value is
    not arbitrary - it is the last time the structure of the nf-core/modules repository was had an
    update breaking backwards compatibility.
    Args:
        module_name (str): Name of module
        per_page (int): Number of commits per page returned by API
        page_nbr (int): Page number of the retrieved commits
        since (str): Only show commits later than this timestamp.
        Time should be given in ISO-8601 format: YYYY-MM-DDTHH:MM:SSZ.

    Returns:
        [ dict ]: List of commit SHAs and associated (truncated) message
    """
    if modules_repo is None:
        modules_repo = ModulesRepo()

    api_url = f"https://api.github.com/repos/{modules_repo.name}/commits?sha=master&path=modules/{module_name}&per_page={per_page}&page={page_nbr}&since={since}"
    log.debug(f"Fetching commit history of module '{module_name}' from github API")
    response = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
    if response.status_code == 200:
        commits = response.json()

        if len(commits) == 0:
            raise UserWarning(f"Reached end of commit history for '{module_name}'")
        else:
            # Return the commit SHAs and the first line of the commit message
            return [
                {"git_sha": commit["sha"], "trunc_message": commit["commit"]["message"].partition("\n")[0]}
                for commit in commits
            ]
    elif response.status_code == 404:
        raise LookupError(f"Module '{module_name}' not found in '{modules_repo.name}'\n{api_url}")
    else:
        raise LookupError(
            f"Unable to fetch commit SHA for module {module_name}. API responded with '{response.status_code}'"
        )


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
    modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "repos": dict()}
    modules_dir = f"{pipeline_dir}/modules"

    # Extract all modules repos in the pipeline directory
    repo_names = [
        f"{user_name}/{repo_name}"
        for user_name in os.listdir(modules_dir)
        if os.path.isdir(os.path.join(modules_dir, user_name)) and user_name != "local"
        for repo_name in os.listdir(os.path.join(modules_dir, user_name))
    ]

    # Get all module names in the repos
    repo_module_names = {
        repo_name: list(
            {
                os.path.relpath(os.path.dirname(path), os.path.join(modules_dir, repo_name))
                for path in glob.glob(f"{modules_dir}/{repo_name}/**/*", recursive=True)
                if os.path.isfile(path)
            }
        )
        for repo_name in repo_names
    }

    progress_bar = rich.progress.Progress(
        "[bold blue]{task.description}",
        rich.progress.BarColumn(bar_width=None),
        "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
        transient=True,
    )
    with progress_bar:
        file_progress = progress_bar.add_task(
            "Creating 'modules.json' file", total=sum(map(len, repo_module_names.values())), test_name="module.json"
        )
        for repo_name, module_names in repo_module_names.items():
            try:
                modules_repo = ModulesRepo(repo=repo_name)
            except LookupError as e:
                raise UserWarning(e)

            repo_path = os.path.join(modules_dir, repo_name)
            modules_json["repos"][repo_name] = dict()
            for module_name in module_names:
                module_path = os.path.join(repo_path, module_name)
                progress_bar.update(file_progress, advance=1, test_name=f"{repo_name}/{module_name}")
                try:
                    # Find the correct commit SHA for the local files.
                    # We iterate over the commit log pages until we either
                    # find a matching commit or we reach the end of the commits
                    correct_commit_sha = None
                    commit_page_nbr = 1
                    while correct_commit_sha is None:

                        commit_shas = [
                            commit["git_sha"]
                            for commit in get_module_git_log(
                                module_name, modules_repo=modules_repo, page_nbr=commit_page_nbr
                            )
                        ]
                        correct_commit_sha = find_correct_commit_sha(
                            module_name, module_path, modules_repo, commit_shas
                        )
                        commit_page_nbr += 1

                    modules_json["repos"][repo_name][module_name] = {"git_sha": correct_commit_sha}
                except (UserWarning, LookupError) as e:
                    log.warn(
                        f"Could not fetch 'git_sha' for module: '{module_name}'. Please try to install a newer version of this module. ({e})"
                    )
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

    module_base_url = f"https://raw.githubusercontent.com/{modules_repo.name}/{commit_sha}/modules/{module_name}"
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


def get_installed_modules(dir, repo_type="modules"):
    """
    Make a list of all modules installed in this repository

    Returns a tuple of two lists, one for local modules
    and one for nf-core modules. The local modules are represented
    as direct filepaths to the module '.nf' file.
    Nf-core module are returned as file paths to the module directories.
    In case the module contains several tools, one path to each tool directory
    is returned.

    returns (local_modules, nfcore_modules)
    """
    # initialize lists
    local_modules = []
    nfcore_modules = []
    local_modules_dir = None
    nfcore_modules_dir = os.path.join(dir, "modules", "nf-core", "modules")

    # Get local modules
    if repo_type == "pipeline":
        local_modules_dir = os.path.join(dir, "modules", "local", "process")

        # Filter local modules
        if os.path.exists(local_modules_dir):
            local_modules = os.listdir(local_modules_dir)
            local_modules = sorted([x for x in local_modules if (x.endswith(".nf") and not x == "functions.nf")])

    # nf-core/modules
    if repo_type == "modules":
        nfcore_modules_dir = os.path.join(dir, "modules")

    # Get nf-core modules
    if os.path.exists(nfcore_modules_dir):
        for m in sorted([m for m in os.listdir(nfcore_modules_dir) if not m == "lib"]):
            if not os.path.isdir(os.path.join(nfcore_modules_dir, m)):
                raise ModuleException(
                    f"File found in '{nfcore_modules_dir}': '{m}'! This directory should only contain module directories."
                )
            m_content = os.listdir(os.path.join(nfcore_modules_dir, m))
            # Not a module, but contains sub-modules
            if not "main.nf" in m_content:
                for tool in m_content:
                    nfcore_modules.append(os.path.join(m, tool))
            else:
                nfcore_modules.append(m)

    # Make full (relative) file paths and create NFCoreModule objects
    local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]
    nfcore_modules = [
        NFCoreModule(os.path.join(nfcore_modules_dir, m), repo_type=repo_type, base_dir=dir) for m in nfcore_modules
    ]

    return local_modules, nfcore_modules


def get_repo_type(dir):
    """
    Determine whether this is a pipeline repository or a clone of
    nf-core/modules
    """
    # Verify that the pipeline dir exists
    if dir is None or not os.path.exists(dir):
        raise LookupError("Could not find directory: {}".format(dir))

    # Determine repository type
    if os.path.exists(os.path.join(dir, "main.nf")):
        return "pipeline"
    elif os.path.exists(os.path.join(dir, "modules")):
        return "modules"
    else:
        raise LookupError("Could not determine repository type of '{}'".format(dir))


def verify_pipeline_dir(dir):
    modules_dir = os.path.join(dir, "modules")
    if os.path.exists(modules_dir):
        repo_names = (
            f"{user}/{repo}"
            for user in os.listdir(modules_dir)
            if user != "local"
            for repo in os.listdir(os.path.join(modules_dir, user))
        )
        missing_remote = []
        modules_is_software = False
        for repo_name in repo_names:
            api_url = f"https://api.github.com/repos/{repo_name}/contents"
            response = requests.get(api_url)
            if response.status_code == 404:
                missing_remote.append(repo_name)
                if repo_name == "nf-core/software":
                    modules_is_software = True

        if len(missing_remote) > 0:
            missing_remote = [f"'{repo_name}'" for repo_name in missing_remote]
            error_msg = "Could not find GitHub repository for: " + ", ".join(missing_remote)
            if modules_is_software:
                error_msg += (
                    "\nAs of version 2.0, remote modules are installed in 'modules/<github user>/<github repo>'"
                )
                error_msg += "\nThe 'nf-core/software' directory should therefore be renamed to 'nf-core/modules'"
            raise UserWarning(error_msg)
