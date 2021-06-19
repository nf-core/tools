import glob
import json
import os
import requests
import sys
import logging

import nf_core.utils

from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


def get_module_git_log(module_name):
    """Fetches the commit history the requested module"""
    api_url = f"https://api.github.com/repos/nf-core/modules/commits?sha=master&path=software/{module_name}"
    response = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
    if response.status_code == 200:
        # Return the commit SHAs and the first line of the commit message
        return [
            {"git_sha": commit["sha"], "trunc_message": commit["commit"]["message"].partition("\n")[0]}
            for commit in response.json()
        ]
    elif response.status_code == 404:
        log.error(f"Module '{module_name}' not found in 'nf-core/modules/'\n{api_url}")
        sys.exit(1)
    else:
        raise SystemError(f"Unable to fetch commit SHA for module {module_name}")


def create_modules_json(pipeline_dir):
    """Create the modules.json files"""
    pipeline_config = nf_core.utils.fetch_wf_config(pipeline_dir)
    pipeline_name = pipeline_config["manifest.name"]
    pipeline_url = pipeline_config["manifest.homePage"]
    modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "modules": {}}
    all_module_file_paths = glob.glob(f"{pipeline_dir}/modules/nf-core/software/**/*", recursive=True)

    # Extract the module paths from the file paths
    module_paths = list(set(map(os.path.dirname, filter(os.path.isfile, all_module_file_paths))))
    module_names = [path.replace(f"{pipeline_dir}/modules/nf-core/software/", "") for path in module_paths]
    module_repo = ModulesRepo()
    for module_name, module_path in zip(module_names, module_paths):
        try:
            commit_shas = [commit["git_sha"] for commit in get_module_git_log(module_name)]
            correct_commit_sha = find_correct_commit_sha(module_name, module_path, module_repo, commit_shas)
            modules_json["modules"][module_name] = {"git_sha": correct_commit_sha}
        except SystemError as e:
            log.error(e)
            log.error("Will not create 'modules.json' file")
            sys.exit(1)
    modules_json_path = os.path.join(pipeline_dir, "modules.json")
    with open(modules_json_path, "w") as fh:
        json.dump(modules_json, fh, indent=4)


def get_module_paths(pipeline_dir):
    base_dir = f"{pipeline_dir}/modules/nf-core/software"


def find_correct_commit_sha(module_name, module_path, modules_repo, commit_shas):
    """Returns the SHA for the latest commit where the local files equal the remote files"""
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
    """Compares the local module files to the module files for the given commit sha"""
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
