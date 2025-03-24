import random
import unittest

import requests

from nf_core.test_datasets.test_datasets_utils import (
    MODULES_BRANCH_NAME,
    GithubApiEndpoints,
    create_download_url,
    create_pretty_nf_path,
    get_remote_branch_names,
    get_remote_tree_for_branch,
    list_files_by_branch,
)


class TestTestDatasetsUtils(unittest.TestCase):
    """Class for components tests"""

    def setUp(self):
        self.gh_urls = GithubApiEndpoints(gh_orga="nf-core", gh_repo="test-datasets")

    def test_modules_branch_exists(self):
        url = self.gh_urls.get_remote_tree_url_for_branch(MODULES_BRANCH_NAME)
        resp = requests.get(url)
        self.assertTrue(resp.ok)
        self.assertTrue(len(resp.json()) != 0)

    def test_get_branch_names(self):
        branch_names = get_remote_branch_names()
        self.assertTrue(len(branch_names) != 0)

    def test_get_remote_tree_for_branch(self):
        # get_remote_tree_for_branch
        file_list = get_remote_tree_for_branch("modules")
        self.assertTrue(len(file_list) != 0)

    def test_list_files_by_branch(self):
        # list_files_by_branch
        tree = list_files_by_branch("modules")
        self.assertTrue(len(tree.values()) != 0)
        self.assertTrue(tree.get("modules", None) is not None)

    def test_create_pretty_nf_path(self):
        # create_pretty_nf_path
        nf_line_modules = create_pretty_nf_path("/foo/bar/file.xyz", is_module_dataset=True)
        nf_line_pipelines = create_pretty_nf_path("/foo/bar/file.xyz", is_module_dataset=False)
        self.assertTrue("module" in nf_line_modules)
        self.assertTrue("pipeline" in nf_line_pipelines)

    def test_create_download_url(self):
        # create_download_url
        test_data_branch = "sarek"
        test_files = get_remote_tree_for_branch(test_data_branch)
        i = random.randint(0, len(test_files))
        url = create_download_url(test_data_branch, test_files[i])
        resp = requests.get(url)
        self.assertTrue(resp.ok)
        self.assertTrue(len(resp.text) != 0)

    def test_github_endpoints(self):
        url_1 = self.gh_urls.get_remote_tree_url_for_branch(MODULES_BRANCH_NAME)
        url_2 = self.gh_urls.get_pipelines_list_url()
        url_3 = self.gh_urls.get_file_download_url(MODULES_BRANCH_NAME, "foo/bar/baz/qerljerlkmf")
        self.assertTrue(url_1 is not None)
        self.assertTrue(url_2 is not None)
        self.assertTrue(url_3 is not None)

        resp_1 = requests.get(url_1)
        resp_2 = requests.get(url_2)
        resp_3 = requests.get(url_3)
        self.assertTrue(resp_1.ok)
        self.assertTrue(resp_2.ok)
        self.assertFalse(resp_3.ok)
