import base64
import logging
import os
import git

from nf_core.utils import NFCORE_DIR, gh_api

log = logging.getLogger(__name__)


class ModulesRepo(object):
    """
    An object to store details about the repository being used for modules.

    Used by the `nf-core modules` top-level command with -r and -b flags,
    so that this can be used in the same way by all sub-commands.
    """

    def __init__(self, repo="nf-core/modules", branch=None, remote=None):
        """
        Initializes the object and clones the git repository if it is not already present
        """

        # Check if name seems to be well formed
        if self.fullname.count("/") != 1:
            raise LookupError(f"Repository name '{self.fullname}' should be of the format '<user>/<repo_name>'")

        self.fullname = repo
        self.branch = branch

        if self.branch is None:
            # Don't bother fetching default branch if we're using nf-core
            if self.fullname == "nf-core/modules":
                self.branch = "master"
            else:
                self.branch = self.get_default_branch()

        if remote is None and self.fullname == "nf-core/modules":
            self.remote = "git@github.com:nf-core/modules.git"

        self.owner, self.name = self.fullname.split("/")
        self.repo = self.setup_local_repo(self.owner, self.name, remote)

        # Verify that the repo seems to be correctly configured
        if self.fullname != "nf-core/modules" or self.branch:
            self.verify_branch()

        self.modules_file_tree = {}
        self.modules_avail_module_names = []

    def setup_local_repo(self, owner, name, remote=None):
        owner_local_dir = os.path.join(NFCORE_DIR, owner)
        if not os.path.exists(owner_local_dir):
            os.makedirs(owner_local_dir)
        self.local_dir = os.path.join(owner_local_dir, name)
        if not os.path.exists(self.local_dir):
            if remote == None:
                raise Exception(
                    f"The git repo {os.path.join(owner, name)} has not been previously used and you did not provide a link to the remote"
                )
            try:
                return git.Repo.clone_from(remote, self.local_dir)
            except git.exc.GitCommandError:
                raise LookupError(f"Failed to clone from the remote: `{remote}`")

        return git.Repo(self.local_dir)

    def get_default_branch(self):
        """Get the default branch for the repo (the branch origin/HEAD is pointing to)"""
        origin_head = next(ref for ref in self.repo.refs if ref == "origin/HEAD")
        _, self.branch = origin_head.ref.name.split("/")

    def verify_branch(self):
        # Check if the branch name exists by trying to check out the branch
        try:
            self.repo.git.checkout(self.branch)
        except git.exc.GitCommandError:
            raise LookupError(f"Branch '{self.branch}' not found in '{self.fullname}'")

        # Make sure the directory is well formed
        dir_names = os.listdir(self.local_dir)
        if "modules" not in dir_names:
            err_str = f"Repository '{self.fullname}' ({self.branch}) does not contain a 'modules/' directory"
            if "software" in dir_names:
                err_str += ".\nAs of version 2.0, the 'software/' directory should be renamed to 'modules/'"
            raise LookupError(err_str)

    def get_modules_file_tree(self):
        """
        Fetch the file list from the repo, using the GitHub API

        Sets self.modules_file_tree
             self.modules_avail_module_names
        """
        api_url = f"https://api.github.com/repos/{self.fullname}/git/trees/{self.branch}?recursive=1"
        r = gh_api.get(api_url)
        if r.status_code == 404:
            raise LookupError(f"Repository / branch not found: {self.fullname} ({self.branch})\n{api_url}")
        elif r.status_code != 200:
            raise LookupError(f"Could not fetch {self.fullname} ({self.branch}) tree: {r.status_code}\n{api_url}")

        result = r.json()
        assert result["truncated"] == False

        self.modules_file_tree = result["tree"]
        for f in result["tree"]:
            if f["path"].startswith("modules/") and f["path"].endswith("/main.nf") and "/test/" not in f["path"]:
                # remove modules/ and /main.nf
                self.modules_avail_module_names.append(f["path"].replace("modules/", "").replace("/main.nf", ""))
        if len(self.modules_avail_module_names) == 0:
            raise LookupError(f"Found no modules in '{self.fullname}'")

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
            if not f["path"].startswith(f"modules/{module}/"):
                continue
            if f["type"] != "blob":
                continue
            if "/test/" in f["path"]:
                continue
            results[f["path"]] = f["url"]
        if commit != "":
            for path in results:
                results[path] = f"https://api.github.com/repos/{self.fullname}/contents/{path}?ref={commit}"
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
        r = gh_api.get(api_url)
        if r.status_code != 200:
            raise LookupError(f"Could not fetch {self.fullname} file: {r.status_code}\n {api_url}")
        result = r.json()
        file_contents = base64.b64decode(result["content"])

        # Write the file contents
        with open(dl_filename, "wb") as fh:
            fh.write(file_contents)
