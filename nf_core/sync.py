#!/usr/bin/env python
"""Synchronise a pipeline TEMPLATE branch with the template.
"""

import git
import json
import logging
import os
import random
import re
import requests
import requests_cache
import rich
import shutil
import time

import nf_core
import nf_core.create
import nf_core.list
import nf_core.sync
import nf_core.utils

log = logging.getLogger(__name__)


class SyncException(Exception):
    """Exception raised when there was an error with TEMPLATE branch synchronisation"""

    pass


class PullRequestException(Exception):
    """Exception raised when there was an error creating a Pull-Request on GitHub.com"""

    pass


class PipelineSync(object):
    """Object to hold syncing information and results.

    Args:
        pipeline_dir (str): The path to the Nextflow pipeline root directory
        from_branch (str): The branch to use to fetch config vars. If not set, will use current active branch
        make_pr (bool): Set this to `True` to create a GitHub pull-request with the changes
        gh_username (str): GitHub username
        gh_repo (str): GitHub repository name

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
    ):
        """Initialise syncing object"""

        self.pipeline_dir = os.path.abspath(pipeline_dir)
        self.from_branch = from_branch
        self.original_branch = None
        self.merge_branch = "nf-core-template-merge-{}".format(nf_core.__version__)
        self.made_changes = False
        self.make_pr = make_pr
        self.gh_pr_returned_data = {}
        self.required_config_vars = ["manifest.name", "manifest.description", "manifest.version", "manifest.author"]

        self.gh_username = gh_username
        self.gh_repo = gh_repo
        self.pr_url = ""

    def sync(self):
        """Find workflow attributes, create a new template pipeline on TEMPLATE"""

        # Clear requests_cache so that we don't get stale API responses
        requests_cache.clear()

        log.info("Pipeline directory: {}".format(self.pipeline_dir))
        if self.from_branch:
            log.info("Using branch '{}' to fetch workflow variables".format(self.from_branch))
        if self.make_pr:
            log.info("Will attempt to automatically create a pull request")

        self.inspect_sync_dir()
        self.get_wf_config()
        self.checkout_template_branch()
        self.delete_template_branch_files()
        self.make_template_pipeline()
        self.commit_template_changes()

        # Push and make a pull request if we've been asked to
        if self.made_changes and self.make_pr:
            try:
                # Check that we have an API auth token
                if os.environ.get("GITHUB_AUTH_TOKEN", "") == "":
                    raise PullRequestException("GITHUB_AUTH_TOKEN not set!")

                # Check that we know the github username and repo name
                if self.gh_username is None and self.gh_repo is None:
                    raise PullRequestException("Could not find GitHub username and repo name")

                self.push_template_branch()
                self.create_merge_base_branch()
                self.push_merge_branch()
                self.make_pull_request()
                self.close_open_template_merge_prs()
            except PullRequestException as e:
                self.reset_target_dir()
                raise PullRequestException(e)

        self.reset_target_dir()

        if not self.made_changes:
            log.info("No changes made to TEMPLATE - sync complete")
        elif not self.make_pr:
            log.info(
                "Now try to merge the updates in to your pipeline:\n  cd {}\n  git merge TEMPLATE".format(
                    self.pipeline_dir
                )
            )

    def inspect_sync_dir(self):
        """Takes a look at the target directory for syncing. Checks that it's a git repo
        and makes sure that there are no uncommitted changes.
        """
        # Check that the pipeline_dir is a git repo
        try:
            self.repo = git.Repo(self.pipeline_dir)
        except git.exc.InvalidGitRepositoryError as e:
            raise SyncException("'{}' does not appear to be a git repository".format(self.pipeline_dir))

        # get current branch so we can switch back later
        self.original_branch = self.repo.active_branch.name
        log.info("Original pipeline repository branch is '{}'".format(self.original_branch))

        # Check to see if there are uncommitted changes on current branch
        if self.repo.is_dirty(untracked_files=True):
            raise SyncException(
                "Uncommitted changes found in pipeline directory!\nPlease commit these before running nf-core sync"
            )

    def get_wf_config(self):
        """Check out the target branch if requested and fetch the nextflow config.
        Check that we have the required config variables.
        """
        # Try to check out target branch (eg. `origin/dev`)
        try:
            if self.from_branch and self.repo.active_branch.name != self.from_branch:
                log.info("Checking out workflow branch '{}'".format(self.from_branch))
                self.repo.git.checkout(self.from_branch)
        except git.exc.GitCommandError:
            raise SyncException("Branch `{}` not found!".format(self.from_branch))

        # If not specified, get the name of the active branch
        if not self.from_branch:
            try:
                self.from_branch = self.repo.active_branch.name
            except git.exc.GitCommandError as e:
                log.error("Could not find active repo branch: ".format(e))

        # Fetch workflow variables
        log.debug("Fetching workflow config variables")
        self.wf_config = nf_core.utils.fetch_wf_config(self.pipeline_dir)

        # Check that we have the required variables
        for rvar in self.required_config_vars:
            if rvar not in self.wf_config:
                raise SyncException("Workflow config variable `{}` not found!".format(rvar))

    def checkout_template_branch(self):
        """
        Try to check out the origin/TEMPLATE in a new TEMPLATE branch.
        If this fails, try to check out an existing local TEMPLATE branch.
        """
        # Try to check out the `TEMPLATE` branch
        try:
            self.repo.git.checkout("origin/TEMPLATE", b="TEMPLATE")
        except git.exc.GitCommandError:
            # Try to check out an existing local branch called TEMPLATE
            try:
                self.repo.git.checkout("TEMPLATE")
            except git.exc.GitCommandError:
                raise SyncException("Could not check out branch 'origin/TEMPLATE' or 'TEMPLATE'")

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
            log.debug("Deleting {}".format(file_path))
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                raise SyncException(e)

    def make_template_pipeline(self):
        """
        Delete all files and make a fresh template using the workflow variables
        """
        log.info("Making a new template pipeline using pipeline variables")

        # Only show error messages from pipeline creation
        logging.getLogger("nf_core.create").setLevel(logging.ERROR)

        nf_core.create.PipelineCreate(
            name=self.wf_config["manifest.name"].strip('"').strip("'"),
            description=self.wf_config["manifest.description"].strip('"').strip("'"),
            version=self.wf_config["manifest.version"].strip('"').strip("'"),
            no_git=True,
            force=True,
            outdir=self.pipeline_dir,
            author=self.wf_config["manifest.author"].strip('"').strip("'"),
        ).init_pipeline()

    def commit_template_changes(self):
        """If we have any changes with the new template files, make a git commit"""
        # Check that we have something to commit
        if not self.repo.is_dirty(untracked_files=True):
            log.info("Template contains no changes - no new commit created")
            return False
        # Commit changes
        try:
            self.repo.git.add(A=True)
            self.repo.index.commit("Template update for nf-core/tools version {}".format(nf_core.__version__))
            self.made_changes = True
            log.info("Committed changes to 'TEMPLATE' branch")
        except Exception as e:
            raise SyncException("Could not commit changes to TEMPLATE:\n{}".format(e))
        return True

    def push_template_branch(self):
        """If we made any changes, push the TEMPLATE branch to the default remote
        and try to make a PR. If we don't have the auth token, try to figure out a URL
        for the PR and print this to the console.
        """
        log.info("Pushing TEMPLATE branch to remote: '{}'".format(os.path.basename(self.pipeline_dir)))
        try:
            self.repo.git.push()
        except git.exc.GitCommandError as e:
            raise PullRequestException("Could not push TEMPLATE branch:\n  {}".format(e))

    def create_merge_base_branch(self):
        """Create a new branch from the updated TEMPLATE branch
        This branch will then be used to create the PR
        """
        # Check if branch exists already
        branch_list = [b.name for b in self.repo.branches]
        if self.merge_branch in branch_list:
            original_merge_branch = self.merge_branch
            # Try to create new branch with number at the end
            # If <branch_name>-2 already exists, increase the number until branch is new
            branch_no = 2
            self.merge_branch = f"{original_merge_branch}-{branch_no}"
            while self.merge_branch in branch_list:
                branch_no += 1
                self.merge_branch = f"{original_merge_branch}-{branch_no}"
            log.info(
                "Branch already existed: '{}', creating branch '{}' instead.".format(
                    original_merge_branch, self.merge_branch
                )
            )

        # Create new branch and checkout
        log.info(f"Checking out merge base branch '{self.merge_branch}'")
        try:
            self.repo.create_head(self.merge_branch)
        except git.exc.GitCommandError as e:
            raise SyncException(f"Could not create new branch '{self.merge_branch}'\n{e}")

    def push_merge_branch(self):
        """Push the newly created merge branch to the remote repository"""
        log.info(f"Pushing '{self.merge_branch}' branch to remote")
        try:
            origin = self.repo.remote()
            origin.push(self.merge_branch)
        except git.exc.GitCommandError as e:
            raise PullRequestException(f"Could not push branch '{self.merge_branch}':\n  {e}")

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
            "[https://nf-co.re/developers/sync](https://nf-co.re/developers/sync#merging-automated-prs).\n\n"
            "For more information about this release of [nf-core/tools](https://github.com/nf-core/tools), "
            "please see the `v{tag}` [release page](https://github.com/nf-core/tools/releases/tag/{tag})."
        ).format(tag=nf_core.__version__)

        # Make new pull-request
        pr_content = {
            "title": pr_title,
            "body": pr_body_text,
            "maintainer_can_modify": True,
            "head": self.merge_branch,
            "base": self.from_branch,
        }

        stderr = rich.console.Console(stderr=True, force_terminal=nf_core.utils.rich_force_colors())

        while True:
            try:
                log.debug("Submitting PR to GitHub API")
                returned_data_prettyprint = ""
                r_headers_pp = ""
                with requests_cache.disabled():
                    r = requests.post(
                        url="https://api.github.com/repos/{}/pulls".format(self.gh_repo),
                        data=json.dumps(pr_content),
                        auth=requests.auth.HTTPBasicAuth(self.gh_username, os.environ["GITHUB_AUTH_TOKEN"]),
                    )
                try:
                    self.gh_pr_returned_data = json.loads(r.content)
                    returned_data_prettyprint = json.dumps(dict(self.gh_pr_returned_data), indent=4)
                    r_headers_pp = json.dumps(dict(r.headers), indent=4)
                except:
                    self.gh_pr_returned_data = r.content
                    returned_data_prettyprint = r.content
                    r_headers_pp = r.headers
                    log.error("Could not parse JSON response from GitHub API!")
                    stderr.print_exception()

                # Dump the responses to the log just in case..
                log.debug(f"PR response from GitHub. Data:\n{returned_data_prettyprint}\n\nHeaders:\n{r_headers_pp}")

                # PR worked
                if r.status_code == 201:
                    self.pr_url = self.gh_pr_returned_data["html_url"]
                    log.debug(f"GitHub API PR worked, return code 201")
                    log.info(f"GitHub PR created: {self.gh_pr_returned_data['html_url']}")
                    break

                # Returned 403 error - too many simultaneous requests
                # https://github.com/nf-core/tools/issues/911
                if r.status_code == 403:
                    log.debug(f"GitHub API PR failed with 403 error")
                    wait_time = float(re.sub("[^0-9]", "", str(r.headers.get("Retry-After", 0))))
                    if wait_time == 0:
                        log.debug("Couldn't find 'Retry-After' header, guessing a length of time to wait")
                        wait_time = random.randrange(10, 60)
                    log.warning(
                        f"Got 403 code - probably the abuse protection. Trying again after {wait_time} seconds.."
                    )
                    time.sleep(wait_time)

                # Something went wrong
                else:
                    raise PullRequestException(
                        f"GitHub API returned code {r.status_code}: \n\n{returned_data_prettyprint}\n\n{r_headers_pp}"
                    )
            # Don't catch the PullRequestException that we raised inside
            except PullRequestException:
                raise
            # Do catch any other exceptions that we hit
            except Exception as e:
                stderr.print_exception()
                raise PullRequestException(
                    f"Something went badly wrong - {e}: \n\n{returned_data_prettyprint}\n\n{r_headers_pp}"
                )

    def close_open_template_merge_prs(self):
        """Get all template merging branches (starting with 'nf-core-template-merge-')
        and check for any open PRs from these branches to the self.from_branch
        If open PRs are found, add a comment and close them
        """
        log.info("Checking for open PRs from template merge branches")

        # Look for existing pull-requests
        list_prs_url = f"https://api.github.com/repos/{self.gh_repo}/pulls"
        with requests_cache.disabled():
            list_prs_request = requests.get(
                url=list_prs_url,
                auth=requests.auth.HTTPBasicAuth(self.gh_username, os.environ["GITHUB_AUTH_TOKEN"]),
            )
        try:
            list_prs_json = json.loads(list_prs_request.content)
            list_prs_pp = json.dumps(list_prs_json, indent=4)
        except:
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
        with requests_cache.disabled():
            comment_request = requests.post(
                url=pr["comments_url"],
                data=json.dumps({"body": comment_text}),
                auth=requests.auth.HTTPBasicAuth(self.gh_username, os.environ["GITHUB_AUTH_TOKEN"]),
            )

        # Update the PR status to be closed
        with requests_cache.disabled():
            pr_request = requests.patch(
                url=pr["url"],
                data=json.dumps({"state": "closed"}),
                auth=requests.auth.HTTPBasicAuth(self.gh_username, os.environ["GITHUB_AUTH_TOKEN"]),
            )
        try:
            pr_request_json = json.loads(pr_request.content)
            pr_request_pp = json.dumps(pr_request_json, indent=4)
        except:
            pr_request_json = pr_request.content
            pr_request_pp = pr_request.content

        # PR update worked
        if pr_request.status_code == 200:
            log.debug("GitHub API PR-update worked:\n{}".format(pr_request_pp))
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
        log.info("Checking out original branch: '{}'".format(self.original_branch))
        try:
            self.repo.git.checkout(self.original_branch)
        except git.exc.GitCommandError as e:
            raise SyncException("Could not reset to original branch `{}`:\n{}".format(self.from_branch, e))
