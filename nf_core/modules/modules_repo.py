import os
import requests
import base64
import sys
import logging
import nf_core.utils

log = logging.getLogger(__name__)


class ModulesRepo(object):
    """
    An object to store details about the repository being used for modules.

    Used by the `nf-core modules` top-level command with -r and -b flags,
    so that this can be used in the same way by all sub-commands.
    """

    def __init__(self, repo="nf-core/modules", branch="master"):
        self.name = repo
        self.branch = branch

        # Verify that the repo seems to be correctly configured
        if self.name != "nf-core/modules" or self.branch != "master":
            try:
                self.verify_modules_repo()
            except LookupError:
                raise

        self.owner, self.repo = self.name.split("/")
        self.modules_file_tree = {}
        self.modules_current_hash = None
        self.modules_avail_module_names = []

    def verify_modules_repo(self):

        # Check if name seems to be well formed
        if self.name.count("/") != 1:
            raise LookupError(f"Repository name '{self.name}' should be of the format '<github_user_name>/<repo_name>'")

        # Check if repository exist
        api_url = f"https://api.github.com/repos/{self.name}/branches"
        response = requests.get(api_url)
        if response.status_code == 200:
            branches = [branch["name"] for branch in response.json()]
            if self.branch not in branches:
                raise LookupError(f"Branch '{self.branch}' not found in '{self.name}'")
        else:
            raise LookupError(f"Repository '{self.name}' is not available on GitHub")

        api_url = f"https://api.github.com/repos/{self.name}/contents?ref={self.branch}"
        response = requests.get(api_url)
        if response.status_code == 200:
            dir_names = [entry["name"] for entry in response.json() if entry["type"] == "dir"]
            if "modules" not in dir_names:
                err_str = f"Repository '{self.name}' ({self.branch}) does not contain a 'modules/' directory"
                if "software" in dir_names:
                    err_str += ".\nAs of version 2.0, the 'software/' directory should be renamed to 'modules/'"
                raise LookupError(err_str)
        else:
            raise LookupError(f"Unable to fetch repository information from '{self.name}' ({self.branch})")

    def get_modules_file_tree(self):
        """
        Fetch the file list from the repo, using the GitHub API

        Sets self.modules_file_tree
             self.modules_current_hash
             self.modules_avail_module_names
        """
        api_url = "https://api.github.com/repos/{}/git/trees/{}?recursive=1".format(self.name, self.branch)
        r = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
        if r.status_code == 404:
            raise LookupError("Repository / branch not found: {} ({})\n{}".format(self.name, self.branch, api_url))
        elif r.status_code != 200:
            raise LookupError(
                "Could not fetch {} ({}) tree: {}\n{}".format(self.name, self.branch, r.status_code, api_url)
            )

        result = r.json()
        assert result["truncated"] == False

        self.modules_current_hash = result["sha"]
        self.modules_file_tree = result["tree"]
        for f in result["tree"]:
            if f["path"].startswith(f"modules/") and f["path"].endswith("/main.nf") and "/test/" not in f["path"]:
                # remove modules/ and /main.nf
                self.modules_avail_module_names.append(f["path"].replace("modules/", "").replace("/main.nf", ""))
        if len(self.modules_avail_module_names) == 0:
            raise LookupError(f"Found no modules in '{self.name}'")

    def get_module_file_urls(self, module, commit=""):
        """Fetch list of URLs for a specific module

        Takes the name of a module and iterates over the GitHub repo file tree.
        Loops over items that are prefixed with the path 'modules/<module_name>' and ignores
        anything that's not a blob. Also ignores the test/ subfolder.

        Returns a dictionary with keys as filenames and values as GitHub API URLs.
        These can be used to then download file contents.

        Args:
            module (string): Name of module for which to fetch a set of URLs

        Returns:
            dict: Set of files and associated URLs as follows:

            {
                'modules/fastqc/main.nf': 'https://api.github.com/repos/nf-core/modules/git/blobs/65ba598119206a2b851b86a9b5880b5476e263c3',
                'modules/fastqc/meta.yml': 'https://api.github.com/repos/nf-core/modules/git/blobs/0d5afc23ba44d44a805c35902febc0a382b17651'
            }
        """
        results = {}
        for f in self.modules_file_tree:
            if not f["path"].startswith("modules/{}".format(module)):
                continue
            if f["type"] != "blob":
                continue
            if "/test/" in f["path"]:
                continue
            results[f["path"]] = f["url"]
        if commit != "":
            for path in results:
                results[path] = f"https://api.github.com/repos/nf-core/modules/contents/{path}?ref={commit}"
        return results

    def download_gh_file(self, dl_filename, api_url):
        """Download a file from GitHub using the GitHub API

        Args:
            dl_filename (string): Path to save file to
            api_url (string): GitHub API URL for file

        Raises:
            If a problem, raises an error
        """

        # Make target directory if it doesn't already exist
        dl_directory = os.path.dirname(dl_filename)
        if not os.path.exists(dl_directory):
            os.makedirs(dl_directory)

        # Call the GitHub API
        r = requests.get(api_url, auth=nf_core.utils.github_api_auto_auth())
        if r.status_code != 200:
            raise LookupError("Could not fetch {} file: {}\n {}".format(self.name, r.status_code, api_url))
        result = r.json()
        file_contents = base64.b64decode(result["content"])

        # Write the file contents
        with open(dl_filename, "wb") as fh:
            fh.write(file_contents)
