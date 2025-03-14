import json
import logging
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)

@dataclass
class GithubApiEndpoints():
    gh_api_base_url = "https://api.github.com/"
    gh_orga: str = "nf-core"
    gh_repo: str = "test-datasets"

    def get_branch_list_url(self, entries_per_page=100):
        url = f"{self.gh_api_base_url}/repos/{self.gh_orga}/{self.gh_repo}/branches?per_page={entries_per_page}"
        return url

    def get_remote_tree_url_for_branch(self, branch, recursive=1):
        url = f"{self.gh_api_base_url}/repos/{self.gh_orga}/{self.gh_repo}/git/trees/{branch}?recursive=1"
        return url


def get_remote_branches():
    """
    List all branches on the remote github repository for test-datasets
    by querying the github API endpoint at `/repos/nf-core/test-datasets/branches`
    """
    gh_api_urls = GithubApiEndpoints(gh_repo="test-datasets")
    response = requests.get(gh_api_urls.get_branch_list_url())

    if not response.ok:
        log.debug(f"Could not fetch list of branches from Github API at url: {response.url}")
        return []

    try:
        resp_json = json.loads(response.text)
        branches = [b["name"] for b in resp_json]
    except KeyError as e:
        log.debug("Could not parse list of branches fetched for   from Github API")
    except json.decoder.JSONDecodeError as e:
        log.debug("Error parsing the list of branches from Github API at url: {response.url}")

    return branches


def get_remote_tree_for_branch():
    """
    For a given branch name, return the file tree by querying the github API
    at the endpoint at `/repos/nf-core/test-datasets/git/trees/`
    """
    pass
