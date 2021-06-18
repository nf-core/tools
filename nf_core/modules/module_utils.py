import requests
import sys
import os
import json
import glob
import logging
import nf_core.utils

log = logging.getLogger(__name__)


def get_module_commit_sha(module_name):
    """Fetches the latests commit SHA for the requested module"""
    api_url = f'https://api.github.com/repos/nf-core/modules/commits/master?q={{path="software/{module_name}"}}'
    response = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
    if response.status_code == 200:
        json_response = response.json()
        return json_response["sha"]
    elif response.status_code == 404:
        log.error(f"Module '{module_name}' not found in 'nf-core/modules/'\n{api_url}")
        sys.exit(1)
    else:
        raise SystemError(f"Unable to fetch commit SHA for module {module_name}")

def create_modules_json_file(pipeline_dir):
    log.info("Creating missing 'modules.json' file.")
    pipeline_config = nf_core.utils.fetch_wf_config(pipeline_dir)
    pipeline_name = pipeline_config["manifest.name"]
    pipeline_url = pipeline_config["manifest.homePage"]
    modules_json = {"name": pipeline_name.strip("'"), "homePage": pipeline_url.strip("'"), "modules": {}}
    module_names = [
        path.replace(f"{pipeline_dir}/modules/nf-core/software/", "")
        for path in glob.glob(f"{pipeline_dir}/modules/nf-core/software/*")
    ]
    for module_name in module_names:
        try:
            commit_sha = get_module_commit_sha(module_name)
            modules_json["modules"][module_name] = {"git_sha": commit_sha}
        except SystemError as e:
            log.error(e)
            log.error("Will not create 'modules.json' file")
            sys.exit(1)
    modules_json_path = os.path.join(pipeline_dir, "modules.json")
    with open(modules_json_path, "w") as fh:
        json.dump(modules_json, fh, indent=4)
