import requests
import sys
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
