import filecmp
import logging
import os
import git
import urllib.parse

from nf_core.utils import NFCORE_DIR, gh_api

log = logging.getLogger(__name__)

# Constants for the nf-core/modules repo used throughout the module files
NF_CORE_MODULES_NAME = "nf-core/modules"
NF_CORE_MODULES_REMOTE = "git@github.com:nf-core/modules.git"


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
            remote_url = NF_CORE_MODULES_REMOTE

        self.remote_url = remote_url

        # Extract the repo path from the remote url
        # See https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-clone.html#URLS for the possible URL patterns
        # Remove the initial `git@`` if it is present
        path = remote_url.split("@")
        path = path[-1] if len(path) > 1 else path[0]
        path = urllib.parse.urlparse(path)
        path = path.path

        self.fullname = os.path.splitext(path)[0]

        self.setup_local_repo(remote_url, branch, no_pull)

        # Verify that the repo seems to be correctly configured
        if self.fullname != NF_CORE_MODULES_NAME or self.branch:
            self.verify_branch()

        # Convenience variable
        self.modules_dir = os.path.join(self.local_repo_dir, "modules")

        self.avail_module_names = None

    def setup_local_repo(self, remote, branch, no_pull=False):
        """
        Sets up the local git repository. If the repository has been cloned previously, it
        returns a git.Repo object of that clone. Otherwise it tries to clone the repository from
        the provided remote URL and returns a git.Repo of the new clone.

        Args:
            remote (str): git url of remote
            branch (str): name of branch to use
            no_pull (bool): Don't pull the repo. (Used for performance reasons)
        Sets self.repo
        """
        self.local_repo_dir = os.path.join(NFCORE_DIR, self.fullname)
        if not os.path.exists(self.local_repo_dir):
            try:
                self.repo = git.Repo.clone_from(remote, self.local_repo_dir)
            except git.exc.GitCommandError:
                raise LookupError(f"Failed to clone from the remote: `{remote}`")
            # Verify that the requested branch exists by checking it out
            self.setup_branch(branch)
        else:
            self.repo = git.Repo(self.local_repo_dir)

            # Verify that the requested branch exists by checking it out
            self.setup_branch(branch)

            # If the repo is already cloned, pull the latest changes from the remote
            if not no_pull:
                self.repo.remotes.origin.pull()

    def setup_branch(self, branch):
        if branch is None:
            # Don't bother fetching default branch if we're using nf-core
            if self.fullname == NF_CORE_MODULES_NAME:
                self.branch = "master"
            else:
                self.branch = self.get_default_branch()
        else:
            self.branch = branch
        # Verify that the branch exists by checking it out
        self.branch_exists()

    def get_default_branch(self):
        """
        Gets the default branch for the repo (the branch origin/HEAD is pointing to)
        """
        origin_head = next(ref for ref in self.repo.refs if ref.name == "origin/HEAD")
        _, self.branch = origin_head.ref.name.split("/")

    def branch_exists(self):
        """Verifies that the branch exists in the repository by trying to check it out"""
        try:
            self.checkout_branch()
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

    def checkout_branch(self):
        """
        Checks out the specified branch of the repository
        """
        self.repo.git.checkout(self.branch)

    def checkout(self, commit):
        """
        Checks out the repository at the requested commit
        """
        self.repo.git.checkout(commit)

    def module_exists(self, module_name):
        """
        Check if a module exists in the branch of the repo

        Returns bool
        """
        return module_name in os.listdir(self.modules_dir)

    def get_module_dir(self, module_name):
        """
        Returns the file path of a module directory in the repo.
        Does not verify that the path exists.

        Returns module_path: str
        """
        return os.path.join(self.modules_dir, module_name)

    def module_files_identical(self, module_name, base_path):
        module_files = ["main.nf", "meta.yml"]
        module_dir = self.get_module_dir(module_name)
        for file in module_files:
            try:
                if not filecmp.cmp(os.path.join(module_dir, file), os.path.join(base_path, file)):
                    return False
            except FileNotFoundError as e:
                log.debug(f"Could not open file: {os.path.join(module_dir, file)}")
                continue
        return True

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
        self.checkout_branch()
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
        self.checkout_branch()
        for commit in self.repo.iter_commits():
            if commit.hexsha == sha:
                message = commit.message.partition("\n")[0]
                date_obj = commit.committed_datetime
                date = str(date_obj.date())
                return message, date
        raise LookupError(f"Commit '{sha}' not found in the '{self.fullname}'")

    def get_avail_modules(self):
        if self.avail_module_names is None:
            # Module directories are characterized by having a 'main.nf' file
            self.avail_module_names = [
                os.path.relpath(dirpath, start=self.modules_dir)
                for dirpath, _, file_names in os.walk(self.modules_dir)
                if "main.nf" in file_names
            ]
        return self.avail_module_names
