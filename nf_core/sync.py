"""Synchronise a pipeline TEMPLATE branch with the template."""

import json
import logging
import os
import re
import shutil

import git
import questionary
import requests
import requests_cache
import rich
import yaml
from git import GitCommandError, InvalidGitRepositoryError

import nf_core
import nf_core.create
import nf_core.list
import nf_core.utils

log = logging.getLogger(__name__)


class SyncExceptionError(Exception):
    """Exception raised when there was an error with TEMPLATE branch synchronisation"""

    pass


class PullRequestExceptionError(Exception):
    """Exception raised when there was an error creating a Pull-Request on GitHub.com"""

    pass


class PipelineSync:
    """Object to hold syncing information and results.

    Args:
        pipeline_dir (str): The path to the Nextflow pipeline root directory
        from_branch (str): The branch to use to fetch config vars. If not set, will use current active branch
        make_pr (bool): Set this to `True` to create a GitHub pull-request with the changes
        gh_username (str): GitHub username
        gh_repo (str): GitHub repository name
        template_yaml_path (str): Path to template.yml file for pipeline creation settings. DEPRECATED
        force_pr (bool): Force the creation of a pull request, even if there are no changes to the template

    Attributes:
        pipeline_dir (str): Path to target pipeline directory
        from_branch (str): Repo branch to use when collecting workflow variables. Default: active branch.
        original_branch (str): Repo branch that was checked out before we started.
        made_changes (bool): Whether making the new template pipeline introduced any changes
        make_pr (bool): Whether to try to automatically make a PR on GitHub.com
        required_config_vars (list): List of nextflow variables required to make template pipeline
        gh_username (str): GitHub username
        gh_repo (str): GitHub repository name
    """

    def __init__(
        self,
        pipeline_dir,
        from_branch=None,
        make_pr=False,
        gh_repo=None,
        gh_username=None,
        template_yaml_path=None,
        force_pr=False,
    ):
        """Initialise syncing object"""

        self.pipeline_dir = os.path.abspath(pipeline_dir)
        self.from_branch = from_branch
        self.original_branch = None
        self.original_merge_branch = f"nf-core-template-merge-{nf_core.__version__}"
        self.merge_branch = self.original_merge_branch
        self.made_changes = False
        self.make_pr = make_pr
        self.gh_pr_returned_data = {}
        self.required_config_vars = ["manifest.name", "manifest.description", "manifest.version", "manifest.author"]
        self.force_pr = force_pr

        self.gh_username = gh_username
        self.gh_repo = gh_repo
        self.pr_url = ""

        self.config_yml_path, self.config_yml = nf_core.utils.load_tools_config(self.pipeline_dir)

        # Throw deprecation warning if template_yaml_path is set
        if template_yaml_path is not None:
            log.warning(
                f"The `template_yaml_path` argument is deprecated. Saving pipeline creation settings in .nf-core.yml instead. Please remove {template_yaml_path} file."
            )
            if "template" in self.config_yml:
                overwrite_template = questionary.confirm(
                    f"A template section already exists in '{self.config_yml_path}'. Do you want to overwrite?",
                    style=nf_core.utils.nfcore_question_style,
                    default=False,
                ).unsafe_ask()
            if overwrite_template or "template" not in self.config_yml:
                with open(template_yaml_path) as f:
                    self.config_yml["template"] = yaml.safe_load(f)
                with open(self.config_yml_path, "w") as fh:
                    yaml.safe_dump(self.config_yml, fh)
                log.info(f"Saved pipeline creation settings to '{self.config_yml_path}'")
                raise SystemExit(
                    f"Please commit your changes and delete the {template_yaml_path} file. Then run the sync command again."
                )

        # Set up the API auth if supplied on the command line
        self.gh_api = nf_core.utils.gh_api
        self.gh_api.lazy_init()
        if self.gh_username and "GITHUB_AUTH_TOKEN" in os.environ:
            log.debug(f"Authenticating sync as {self.gh_username}")
            self.gh_api.setup_github_auth(
                requests.auth.HTTPBasicAuth(self.gh_username, os.environ["GITHUB_AUTH_TOKEN"])
            )

    def sync(self):
        """Find workflow attributes, create a new template pipeline on TEMPLATE"""

        # Clear requests_cache so that we don't get stale API responses
        requests_cache.clear()

        log.info(f"Pipeline directory: {self.pipeline_dir}")
        if self.from_branch:
            log.info(f"Using branch '{self.from_branch}' to fetch workflow variables")
        if self.make_pr:
            log.info("Will attempt to automatically create a pull request")

        self.inspect_sync_dir()
        self.get_wf_config()
        self.checkout_template_branch()
        self.delete_template_branch_files()
        self.make_template_pipeline()
        self.commit_template_changes()

        if not self.made_changes and self.force_pr:
            log.info("No changes made to TEMPLATE, but PR forced")
            self.made_changes = True

        # Push and make a pull request if we've been asked to
        if self.made_changes and self.make_pr or self.force_pr:
            try:
                # Check that we have an API auth token
                if os.environ.get("GITHUB_AUTH_TOKEN", "") == "":
                    raise PullRequestExceptionError("GITHUB_AUTH_TOKEN not set!")

                # Check that we know the github username and repo name
                if self.gh_username is None and self.gh_repo is None:
                    raise PullRequestExceptionError("Could not find GitHub username and repo name")

                self.push_template_branch()
                self.create_merge_base_branch()
                self.push_merge_branch()
                self.make_pull_request()
                self.close_open_template_merge_prs()
            except PullRequestExceptionError as e:
                self.reset_target_dir()
                raise PullRequestExceptionError(e)

        self.reset_target_dir()

        if not self.made_changes:
            log.info("No changes made to TEMPLATE - sync complete")
        elif not self.make_pr:
            log.info(
                f"Now try to merge the updates in to your pipeline:\n  cd {self.pipeline_dir}\n  git merge TEMPLATE"
            )

    def inspect_sync_dir(self):
        """Takes a look at the target directory for syncing. Checks that it's a git repo
        and makes sure that there are no uncommitted changes.
        """
        # Check that the pipeline_dir is a git repo
        try:
            self.repo = git.Repo(self.pipeline_dir)
        except InvalidGitRepositoryError:
            raise SyncExceptionError(f"'{self.pipeline_dir}' does not appear to be a git repository")

        # get current branch so we can switch back later
        self.original_branch = self.repo.active_branch.name
        log.info(f"Original pipeline repository branch is '{self.original_branch}'")

        # Check to see if there are uncommitted changes on current branch
        if self.repo.is_dirty(untracked_files=True):
            raise SyncExceptionError(
                "Uncommitted changes found in pipeline directory!\nPlease commit these before running nf-core sync"
            )

    def get_wf_config(self):
        """Check out the target branch if requested and fetch the nextflow config.
        Check that we have the required config variables.
        """
        # Try to check out target branch (eg. `origin/dev`)
        try:
            if self.from_branch and self.repo.active_branch.name != self.from_branch:
                log.info(f"Checking out workflow branch '{self.from_branch}'")
                self.repo.git.checkout(self.from_branch)
        except GitCommandError:
            raise SyncExceptionError(f"Branch `{self.from_branch}` not found!")

        # If not specified, get the name of the active branch
        if not self.from_branch:
            try:
                self.from_branch = self.repo.active_branch.name
            except GitCommandError as e:
                log.error(f"Could not find active repo branch: {e}")

        # Fetch workflow variables
        log.debug("Fetching workflow config variables")
        self.wf_config = nf_core.utils.fetch_wf_config(self.pipeline_dir)

        # Check that we have the required variables
        for rvar in self.required_config_vars:
            if rvar not in self.wf_config:
                raise SyncExceptionError(f"Workflow config variable `{rvar}` not found!")

    def checkout_template_branch(self):
        """
        Try to check out the origin/TEMPLATE in a new TEMPLATE branch.
        If this fails, try to check out an existing local TEMPLATE branch.
        """
        # Try to check out the `TEMPLATE` branch
        try:
            self.repo.git.checkout("origin/TEMPLATE", b="TEMPLATE")
        except GitCommandError:
            # Try to check out an existing local branch called TEMPLATE
            try:
                self.repo.git.checkout("TEMPLATE")
            except GitCommandError:
                raise SyncExceptionError("Could not check out branch 'origin/TEMPLATE' or 'TEMPLATE'")

    def delete_template_branch_files(self):
        """
        Delete all files in the TEMPLATE branch
        """
        # Delete everything
        log.info("Deleting all files in 'TEMPLATE' branch")
        for the_file in os.listdir(self.pipeline_dir):
            if the_file == ".git":
                continue
            file_path = os.path.join(self.pipeline_dir, the_file)
            log.debug(f"Deleting {file_path}")
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                raise SyncExceptionError(e)

    def make_template_pipeline(self):
        """
        Delete all files and make a fresh template using the workflow variables
        """
        log.info("Making a new template pipeline using pipeline variables")

        # Only show error messages from pipeline creation
        logging.getLogger("nf_core.create").setLevel(logging.ERROR)

        # Re-write the template yaml info from .nf-core.yml config
        if "template" in self.config_yml:
            with open(self.config_yml_path, "w") as config_path:
                yaml.safe_dump(self.config_yml, config_path)

        try:
            nf_core.create.PipelineCreate(
                name=self.wf_config["manifest.name"].strip('"').strip("'"),
                description=self.wf_config["manifest.description"].strip('"').strip("'"),
                version=self.wf_config["manifest.version"].strip('"').strip("'"),
                no_git=True,
                force=True,
                outdir=self.pipeline_dir,
                author=self.wf_config["manifest.author"].strip('"').strip("'"),
                plain=True,
            ).init_pipeline()
        except Exception as err:
            # Reset to where you were to prevent git getting messed up.
            self.repo.git.reset("--hard")
            raise SyncExceptionError(f"Failed to rebuild pipeline from template with error:\n{err}")

    def commit_template_changes(self):
        """If we have any changes with the new template files, make a git commit"""
        # Check that we have something to commit
        if not self.repo.is_dirty(untracked_files=True):
            log.info("Template contains no changes - no new commit created")
            return False
        # Commit changes
        try:
            self.repo.git.add(A=True)
            self.repo.index.commit(f"Template update for nf-core/tools version {nf_core.__version__}")
            self.made_changes = True
            log.info("Committed changes to 'TEMPLATE' branch")
        except Exception as e:
            raise SyncExceptionError(f"Could not commit changes to TEMPLATE:\n{e}")
        return True

    def push_template_branch(self):
        """If we made any changes, push the TEMPLATE branch to the default remote
        and try to make a PR. If we don't have the auth token, try to figure out a URL
        for the PR and print this to the console.
        """
        log.info(f"Pushing TEMPLATE branch to remote: '{os.path.basename(self.pipeline_dir)}'")
        try:
            self.repo.git.push()
        except GitCommandError as e:
            raise PullRequestExceptionError(f"Could not push TEMPLATE branch:\n  {e}")

    def create_merge_base_branch(self):
        """Create a new branch from the updated TEMPLATE branch
        This branch will then be used to create the PR
        """
        # Check if branch exists already
        branch_list = [b.name for b in self.repo.branches]
        if self.merge_branch in branch_list:
            merge_branch_format = re.compile(rf"{self.original_merge_branch}-(\d+)")
            max_branch = max(
                [1]
                + [
                    int(merge_branch_format.match(branch).groups()[0])
                    for branch in branch_list
                    if merge_branch_format.match(branch)
                ]
            )
            new_branch = f"{self.original_merge_branch}-{max_branch+1}"
            log.info(f"Branch already existed: '{self.merge_branch}', creating branch '{new_branch}' instead.")
            self.merge_branch = new_branch

        # Create new branch and checkout
        log.info(f"Checking out merge base branch '{self.merge_branch}'")
        try:
            self.repo.create_head(self.merge_branch)
        except GitCommandError as e:
            raise SyncExceptionError(f"Could not create new branch '{self.merge_branch}'\n{e}")

    def push_merge_branch(self):
        """Push the newly created merge branch to the remote repository"""
        log.info(f"Pushing '{self.merge_branch}' branch to remote")
        try:
            origin = self.repo.remote()
            origin.push(self.merge_branch)
        except GitCommandError as e:
            raise PullRequestExceptionError(f"Could not push branch '{self.merge_branch}':\n  {e}")

    def make_pull_request(self):
        """Create a pull request to a base branch (default: dev),
        from a head branch (default: TEMPLATE)

        Returns: An instance of class requests.Response
        """
        log.info("Submitting a pull request via the GitHub API")

        pr_title = f"Important! Template update for nf-core/tools v{nf_core.__version__}"
        pr_body_text = (
            "Version `{tag}` of [nf-core/tools](https://github.com/nf-core/tools) has just been released with updates to the nf-core template. "
            "This automated pull-request attempts to apply the relevant updates to this pipeline.\n\n"
            "Please make sure to merge this pull-request as soon as possible, "
            f"resolving any merge conflicts in the `{self.merge_branch}` branch (or your own fork, if you prefer). "
            "Once complete, make a new minor release of your pipeline.\n\n"
            "For instructions on how to merge this PR, please see "
            "[https://nf-co.re/docs/contributing/sync/](https://nf-co.re/docs/contributing/sync/#merging-automated-prs).\n\n"
            "For more information about this release of [nf-core/tools](https://github.com/nf-core/tools), "
            "please see the `v{tag}` [release page](https://github.com/nf-core/tools/releases/tag/{tag})."
        ).format(tag=nf_core.__version__)

        # Make new pull-request
        stderr = rich.console.Console(stderr=True, force_terminal=nf_core.utils.rich_force_colors())
        with self.gh_api.cache_disabled():
            try:
                r = self.gh_api.request_retry(
                    f"https://api.github.com/repos/{self.gh_repo}/pulls",
                    post_data={
                        "title": pr_title,
                        "body": pr_body_text,
                        "maintainer_can_modify": True,
                        "head": self.merge_branch,
                        "base": self.from_branch,
                    },
                )
            except Exception as e:
                stderr.print_exception()
                raise PullRequestExceptionError(f"Something went badly wrong - {e}")
            else:
                self.gh_pr_returned_data = r.json()
                self.pr_url = self.gh_pr_returned_data["html_url"]
                log.debug(f"GitHub API PR worked, return code {r.status_code}")
                log.info(f"GitHub PR created: {self.gh_pr_returned_data['html_url']}")

    def close_open_template_merge_prs(self):
        """Get all template merging branches (starting with 'nf-core-template-merge-')
        and check for any open PRs from these branches to the self.from_branch
        If open PRs are found, add a comment and close them
        """
        log.info("Checking for open PRs from template merge branches")

        # Look for existing pull-requests
        list_prs_url = f"https://api.github.com/repos/{self.gh_repo}/pulls"
        with self.gh_api.cache_disabled():
            list_prs_request = self.gh_api.get(list_prs_url)
        try:
            list_prs_json = json.loads(list_prs_request.content)
            list_prs_pp = json.dumps(list_prs_json, indent=4)
        except Exception:
            list_prs_json = list_prs_request.content
            list_prs_pp = list_prs_request.content

        log.debug(f"GitHub API listing existing PRs:\n{list_prs_url}\n{list_prs_pp}")
        if list_prs_request.status_code != 200:
            log.warning(f"Could not list open PRs ('{list_prs_request.status_code}')\n{list_prs_url}\n{list_prs_pp}")
            return False

        for pr in list_prs_json:
            log.debug(f"Looking at PR from '{pr['head']['ref']}': {pr['html_url']}")
            # Ignore closed PRs
            if pr["state"] != "open":
                log.debug(f"Ignoring PR as state not open ({pr['state']}): {pr['html_url']}")
                continue

            # Don't close the new PR that we just opened
            if pr["head"]["ref"] == self.merge_branch:
                continue

            # PR is from an automated branch and goes to our target base
            if pr["head"]["ref"].startswith("nf-core-template-merge-") and pr["base"]["ref"] == self.from_branch:
                self.close_open_pr(pr)

    def close_open_pr(self, pr):
        """Given a PR API response, add a comment and close."""
        log.debug(f"Attempting to close PR: '{pr['html_url']}'")

        # Make a new comment explaining why the PR is being closed
        comment_text = (
            f"Version `{nf_core.__version__}` of the [nf-core/tools](https://github.com/nf-core/tools) pipeline template has just been released. "
            f"This pull-request is now outdated and has been closed in favour of {self.pr_url}\n\n"
            f"Please use {self.pr_url} to merge in the new changes from the nf-core template as soon as possible."
        )
        with self.gh_api.cache_disabled():
            self.gh_api.post(url=pr["comments_url"], data=json.dumps({"body": comment_text}))

        # Update the PR status to be closed
        with self.gh_api.cache_disabled():
            pr_request = self.gh_api.patch(url=pr["url"], data=json.dumps({"state": "closed"}))
        try:
            pr_request_json = json.loads(pr_request.content)
            pr_request_pp = json.dumps(pr_request_json, indent=4)
        except Exception:
            pr_request_json = pr_request.content
            pr_request_pp = pr_request.content

        # PR update worked
        if pr_request.status_code == 200:
            log.debug(f"GitHub API PR-update worked:\n{pr_request_pp}")
            log.info(
                f"Closed GitHub PR from '{pr['head']['ref']}' to '{pr['base']['ref']}': {pr_request_json['html_url']}"
            )
            return True
        # Something went wrong
        else:
            log.warning(f"Could not close PR ('{pr_request.status_code}'):\n{pr['url']}\n{pr_request_pp}")
            return False

    def reset_target_dir(self):
        """
        Reset the target pipeline directory. Check out the original branch.
        """
        log.info(f"Checking out original branch: '{self.original_branch}'")
        try:
            self.repo.git.checkout(self.original_branch)
        except GitCommandError as e:
            raise SyncExceptionError(f"Could not reset to original branch `{self.original_branch}`:\n{e}")
