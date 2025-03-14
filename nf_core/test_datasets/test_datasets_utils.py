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

    try:
        gh_api_urls = GithubApiEndpoints(gh_repo="test-datasets")
        response = requests.get(gh_api_urls.get_branch_list_url())

        if not response.ok:
            log.error(f"Error status code {response.status_code} received while fetching the list of branches at url: {response.url}")
            return []

        resp_json = json.loads(response.text)
        branches = [b["name"] for b in resp_json]

    except requests.exceptions.RequestException as e:
        log.error("Error while handling request to url {gh_api_url}", e)
    except KeyError as e:
        log.error("Error parsing the list of branches received from Github API", e)
    except json.decoder.JSONDecodeError as e:
        log.error("Error parsing the list of branches received from Github API at url {response.url} as json",  e)

    return branches


def get_remote_tree_for_branch(branch, only_files=True, ignored_prefixes=[]):
    """
    For a given branch name, return the file tree by querying the github API
    at the endpoint at `/repos/nf-core/test-datasets/git/trees/`
    """

    gh_filetree_file_value = "blob"    # value in nodes used to refer to "files"
    gh_response_filetree_key = "tree"  # key in response to refer to the filetree
    gh_filetree_type_key = "type"      # key in filetree nodes used to refer to their type
    gh_filetree_name_key = "path"      # key in filetree nodes used to refer to their name


    try:
        gh_api_url = GithubApiEndpoints(gh_repo="test-datasets")
        response = requests.get(gh_api_url.get_remote_tree_url_for_branch(branch))

        if not response.ok:
            log.error(f"Error status code {response.status_code} received while fetching the repository filetree at url {response.url}")
            return []

        repo_tree = json.loads(response.text)[gh_response_filetree_key]

        if only_files:
            repo_tree = [node for node in repo_tree if node[gh_filetree_type_key] == gh_filetree_file_value]

        if len(ignored_prefixes):
            repo_tree = [node for node in repo_tree for prefix in ignored_prefixes if not node[gh_filetree_name_key].startswith(prefix)]

        # extract only the names
        repo_files = [node[gh_filetree_name_key] for node in repo_tree]

    except requests.exceptions.RequestException as e:
        log.error("Error while handling request to url {gh_api_url}", e)

    except json.decoder.JSONDecodeError as e:
        log.error("Error parsing the repository filetree received from Github API at url {response.url} as json", e)

    return repo_files