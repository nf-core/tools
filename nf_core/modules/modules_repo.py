import base64
import logging
import os
import git
import urllib.parse

from nf_core.utils import NFCORE_DIR, gh_api

log = logging.getLogger(__name__)


class ModulesRepo(object):
    """
    An object to store details about the repository being used for modules.

    Used by the `nf-core modules` top-level command with -r and -b flags,
    so that this can be used in the same way by all sub-commands.
    """

    def __init__(self, remote_url=None, branch=None, no_pull=False):
        """
        Initializes the object and clones the git repository if it is not already present
        """

        # Check if the remote seems to be well formed
        if remote_url is None:
            remote_url = "git@github.com:nf-core/modules.git"

        # Extract the repo path from the remote url
        # See https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-clone.html#URLS for the possible URL patterns
        # Remove the initial `git@`` if it is present
        path = remote_url.split("@")
        path = path[-1] if len(path) > 1 else path[0]
        path = urllib.parse.urlparse(path)
        path = path.path

        self.fullname = os.path.splitext(path)[0]
        self.branch = branch

        if self.branch is None:
            # Don't bother fetching default branch if we're using nf-core
            if self.fullname == "nf-core/modules":
                self.branch = "master"
            else:
                self.branch = self.get_default_branch()

        self.setup_local_repo(remote_url, no_pull)

        # Verify that the repo seems to be correctly configured
        if self.fullname != "nf-core/modules" or self.branch:
            self.verify_branch()

        self.modules_file_tree = {}
        self.modules_avail_module_names = []

    def setup_local_repo(self, remote, no_pull):
        """
        Sets up the local git repository. If the repository has been cloned previously, it
        returns a git.Repo object of that clone. Otherwise it tries to clone the repository from
        the provided remote URL and returns a git.Repo of the new clone.

        Sets self.repo
        """
        self.local_repo_dir = os.path.join(NFCORE_DIR, self.fullname)
        if not os.path.exists(self.local_repo_dir):
            try:
                self.repo = git.Repo.clone_from(remote, self.local_repo_dir)
            except git.exc.GitCommandError:
                raise LookupError(f"Failed to clone from the remote: `{remote}`")
            # Verify that the requested branch exists by checking it out
            self.branch_exists()
        else:
            self.repo = git.Repo(self.local_repo_dir)

            # Verify that the requested branch exists by checking it out
            self.branch_exists()

            # If the repo is already cloned, pull the latest changes from the remote
            if not no_pull:
                self.repo.remotes.origin.pull()

    def get_default_branch(self):
        """
        Gets the default branch for the repo (the branch origin/HEAD is pointing to)
        """
        origin_head = next(ref for ref in self.repo.refs if ref == "origin/HEAD")
        _, self.branch = origin_head.ref.name.split("/")

    def branch_exists(self):
        """Verifies that the branch exists in the repository by trying to check it out"""
        try:
            self.repo.git.checkout(self.branch)
        except git.exc.GitCommandError:
            raise LookupError(f"Branch '{self.branch}' not found in '{self.fullname}'")

    def verify_branch(self):
        """
        Verifies the active branch conforms do the correct directory structure
        """
        dir_names = os.listdir(self.local_repo_dir)
        if "modules" not in dir_names:
            err_str = f"Repository '{self.fullname}' ({self.branch}) does not contain a 'modules/' directory"
            if "software" in dir_names:
                err_str += ".\nAs of version 2.0, the 'software/' directory should be renamed to 'modules/'"
            raise LookupError(err_str)

    def branch_checkout(self):
        """
        Checks out the specified branch of the repository
        """
        self.repo.git.checkout(self.branch)

    def checkout(self, ref):
        """
        Checks out the repository at the requested ref
        """
        self.repo.git.checkout(ref)

    def module_exists(self, module_name):
        """
        Check if a module exists in the branch of the repo

        Returns bool
        """
        return module_name in os.listdir(os.path.join(self.local_repo_dir, "modules"))

    def get_module_dir(self, module_name):
        """
        Returns the file path of a module directory in the repo.
        Does not verify that the path exists.

        Returns module_path: str
        """
        return os.path.join(self.local_repo_dir, "modules", module_name)

    def get_module_files(self, module_name, files):
        """
        Returns the contents requested files for a module at the current
        checked out ref

        Returns contents: [ str ]
        """

        contents = [None] * len(files)
        module_path = self.get_module_dir(module_name)
        for i, file in enumerate(files):
            try:
                contents[i] = open(os.path.join(module_path, file), "r").read()
            except FileNotFoundError as e:
                log.debug(f"Could not open file: {os.path.join(module_path, file)}")
                continue
        return contents

    def get_module_git_log(self, module_name, depth=None, since="2021-07-07T00:00:00Z"):
        """
        Fetches the commit history the of requested module since a given date. The default value is
        not arbitrary - it is the last time the structure of the nf-core/modules repository was had an
        update breaking backwards compatibility.
        Args:
            module_name (str): Name of module
            modules_repo (ModulesRepo): A ModulesRepo object configured for the repository in question
            per_page (int): Number of commits per page returned by API
            page_nbr (int): Page number of the retrieved commits
            since (str): Only show commits later than this timestamp.
            Time should be given in ISO-8601 format: YYYY-MM-DDTHH:MM:SSZ.

        Returns:
            ( dict ): Iterator of commit SHAs and associated (truncated) message
        """
        module_path = os.path.join("modules", module_name)
        commits = self.repo.iter_commits(max_count=depth, paths=module_path)
        commits = ({"git_sha": commit.hexsha, "trunc_message": commit.message.partition("\n")[0]} for commit in commits)
        return commits

    def sha_exists_on_branch(self, sha):
        """
        Verifies that a given commit sha exists on the branch
        """
        self.checkout()
        return sha in (commit.hexsha for commit in self.repo.iter_commits())

    def get_commit_info(self, sha):
        """
        Fetches metadata about the commit (dates, message, etc.)
        Args:
            commit_sha (str): The SHA of the requested commit
        Returns:
            message (str): The commit message for the requested commit
            date (str): The commit date for the requested commit
        Raises:
            LookupError: If the search for the commit fails
        """
        self.branch_checkout()
        for commit in self.repo.iter_commits():
            if commit.hexsha == sha:
                message = commit.message.partition("\n")[0]
                date_obj = commit.committed_datetime
                date = str(date_obj.date())
                return message, date
        raise LookupError(f"Commit '{sha}' not found in the '{self.fullname}'")

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
