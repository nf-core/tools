import unittest

import responses

from nf_core.test_datasets.list import list_datasets
from nf_core.test_datasets.test_datasets_utils import (
    MODULES_BRANCH_NAME,
    GithubApiEndpoints,
)


def mock_get_pipelines_request(rsps: responses.RequestsMock) -> None:
    """
    Mock request to list pipelines
    """
    url = "https://raw.githubusercontent.com/nf-core/website/refs/heads/main/public/pipeline_names.json"
    resp_json = {
        "pipeline": [
            "airrflow",
            "ampliseq",
            "atacseq",
            "bacass",
            "bactmap",
        ]
    }

    # add dummy json response at given url for get request
    rsps.add(method="GET", url=url, json=resp_json, status=200)


def mock_gh_api_request(rsps: responses.RequestsMock, branch=MODULES_BRANCH_NAME) -> None:
    """
    Mock request to list files in a github branch
    """
    gh_urls = GithubApiEndpoints(gh_orga="nf-core", gh_repo="test-datasets")

    # output from requets for modules files
    resp_json = {
        "sha": "bd061d2421282afa00ae1c83b43151fda0e046b7",
        "url": "https://api.github.com/repos/nf-core/test-datasets/git/trees/bd061d2421282afa00ae1c83b43151fda0e046b7",
        "tree": [
            {
                "path": "README.md",
                "type": "blob",
                "url": "https://api.github.com/repos/nf-core/test-datasets/git/blobs/1ebf7eb543cbb09b875a8a1ef50e107c5cfa8310",
            },
            {
                "path": "assemblies",
                "type": "tree",
                "url": "https://api.github.com/repos/nf-core/test-datasets/git/trees/fdf5797e56e51b5e0bbd583e8499ef660204a194",
            },
            {
                "path": "assemblies/MEGAHIT-test_minigut.contigs.fa.gz",
                "type": "blob",
                "url": "https://api.github.com/repos/nf-core/test-datasets/git/blobs/83185a06b64158a5ea144b8a5a4c26499cd3f585",
            },
            {
                "path": "samplesheets/assembly_samplesheet.csv",
                "type": "blob",
                "url": "https://api.github.com/repos/nf-core/test-datasets/git/blobs/0b86b23c3f901103a1a72ec9953a67623cd90e3e",
            },
        ],
    }

    # Add dummy json response at gh url with ok status code
    rsps.add(method="GET", url=gh_urls.get_remote_tree_url_for_branch(branch), json=resp_json, status=200)


class TestTestDatasetsList(unittest.TestCase):
    def test_list_datasets(self):
        with responses.RequestsMock() as rsps:
            branch = MODULES_BRANCH_NAME
            mock_get_pipelines_request(rsps)
            mock_gh_api_request(rsps, branch=branch)
            res = list_datasets(maybe_branch=branch)
            assert res is None
