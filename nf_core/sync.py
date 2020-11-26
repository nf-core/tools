#!/usr/bin/env python
"""Synchronise a pipeline TEMPLATE branch with the template.
"""

import click
import git
import json
import logging
import os
import re
import requests
import shutil
import tempfile

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
        """ Initialise syncing object """

        self.pipeline_dir = os.path.abspath(pipeline_dir)
        self.from_branch = from_branch
        self.original_branch = None
        self.made_changes = False
        self.make_pr = make_pr
        self.gh_pr_returned_data = {}
        self.required_config_vars = ["manifest.name", "manifest.description", "manifest.version", "manifest.author"]

        self.gh_username = gh_username
        self.gh_repo = gh_repo

    def sync(self):
        """Find workflow attributes, create a new template pipeline on TEMPLATE"""

        log.info("Pipeline directory: {}".format(self.pipeline_dir))
        if self.from_branch:
            log.info("Using branch `{}` to fetch workflow variables".format(self.from_branch))
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
                self.push_template_branch()
                self.make_pull_request()
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
        log.info("Deleting all files in TEMPLATE branch")
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
            new_version=self.wf_config["manifest.version"].strip('"').strip("'"),
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
            log.info("Committed changes to TEMPLATE branch")
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

    def make_pull_request(self):
        """Create a pull request to a base branch (default: dev),
        from a head branch (default: TEMPLATE)

        Returns: An instance of class requests.Response
        """
        # Check that we know the github username and repo name
        try:
            assert self.gh_username is not None
            assert self.gh_repo is not None
        except AssertionError:
            raise PullRequestException("Could not find GitHub username and repo name")

        # If we've been asked to make a PR, check that we have the credentials
        try:
            assert os.environ.get("GITHUB_AUTH_TOKEN", "") != ""
        except AssertionError:
            raise PullRequestException(
                "Environment variable GITHUB_AUTH_TOKEN not set - cannot make PR\n"
                "Make a PR at the following URL:\n  https://github.com/{}/compare/{}...TEMPLATE".format(
                    self.gh_repo, self.original_branch
                )
            )

        log.info("Submitting a pull request via the GitHub API")

        pr_title = "Important! Template update for nf-core/tools v{}".format(nf_core.__version__)
        pr_body_text = (
            "A new release of the main template in nf-core/tools has just been released. "
            "This automated pull-request attempts to apply the relevant updates to this pipeline.\n\n"
            "Please make sure to merge this pull-request as soon as possible. "
            "Once complete, make a new minor release of your pipeline. "
            "For instructions on how to merge this PR, please see "
            "[https://nf-co.re/developers/sync](https://nf-co.re/developers/sync#merging-automated-prs).\n\n"
            "For more information about this release of [nf-core/tools](https://github.com/nf-core/tools), "
            "please see the [nf-core/tools v{tag} release page](https://github.com/nf-core/tools/releases/tag/{tag})."
        ).format(tag=nf_core.__version__)

        # Try to update an existing pull-request
        if self.update_existing_pull_request(pr_title, pr_body_text) is False:
            # None found - make a new pull-request
            self.submit_pull_request(pr_title, pr_body_text)

    def update_existing_pull_request(self, pr_title, pr_body_text):
        """
        List existing pull-requests between TEMPLATE and self.from_branch

        If one is found, attempt to update it with a new title and body text
        If none are found, return False
        """
        assert os.environ.get("GITHUB_AUTH_TOKEN", "") != ""
        # Look for existing pull-requests
        list_prs_url = "https://api.github.com/repos/{}/pulls?head=nf-core:TEMPLATE&base={}".format(
            self.gh_repo, self.from_branch
        )
        r = requests.get(
            url=list_prs_url,
            auth=requests.auth.HTTPBasicAuth(self.gh_username, os.environ.get("GITHUB_AUTH_TOKEN")),
        )
        try:
            r_json = json.loads(r.content)
            r_pp = json.dumps(r_json, indent=4)
        except:
            r_json = r.content
            r_pp = r.content

        # PR worked
        if r.status_code == 200:
            log.debug("GitHub API listing existing PRs:\n{}".format(r_pp))

            # No open PRs
            if len(r_json) == 0:
                log.info("No open PRs found between TEMPLATE and {}".format(self.from_branch))
                return False

            # Update existing PR
            pr_update_api_url = r_json[0]["url"]
            pr_content = {"title": pr_title, "body": pr_body_text}

            r = requests.patch(
                url=pr_update_api_url,
                data=json.dumps(pr_content),
                auth=requests.auth.HTTPBasicAuth(self.gh_username, os.environ.get("GITHUB_AUTH_TOKEN")),
            )
            try:
                r_json = json.loads(r.content)
                r_pp = json.dumps(r_json, indent=4)
            except:
                r_json = r.content
                r_pp = r.content

            # PR update worked
            if r.status_code == 200:
                log.debug("GitHub API PR-update worked:\n{}".format(r_pp))
                log.info("Updated GitHub PR: {}".format(r_json["html_url"]))
                return True
            # Something went wrong
            else:
                log.warning("Could not update PR ('{}'):\n{}\n{}".format(r.status_code, pr_update_api_url, r_pp))
                return False

        # Something went wrong
        else:
            log.warning("Could not list open PRs ('{}')\n{}\n{}".format(r.status_code, list_prs_url, r_pp))
            return False

    def submit_pull_request(self, pr_title, pr_body_text):
        """
        Create a new pull-request on GitHub
        """
        assert os.environ.get("GITHUB_AUTH_TOKEN", "") != ""
        pr_content = {
            "title": pr_title,
            "body": pr_body_text,
            "maintainer_can_modify": True,
            "head": "TEMPLATE",
            "base": self.from_branch,
        }

        r = requests.post(
            url="https://api.github.com/repos/{}/pulls".format(self.gh_repo),
            data=json.dumps(pr_content),
            auth=requests.auth.HTTPBasicAuth(self.gh_username, os.environ.get("GITHUB_AUTH_TOKEN")),
        )
        try:
            self.gh_pr_returned_data = json.loads(r.content)
            returned_data_prettyprint = json.dumps(self.gh_pr_returned_data, indent=4)
        except:
            self.gh_pr_returned_data = r.content
            returned_data_prettyprint = r.content

        # PR worked
        if r.status_code == 201:
            log.debug("GitHub API PR worked:\n{}".format(returned_data_prettyprint))
            log.info("GitHub PR created: {}".format(self.gh_pr_returned_data["html_url"]))

        # Something went wrong
        else:
            raise PullRequestException(
                "GitHub API returned code {}: \n{}".format(r.status_code, returned_data_prettyprint)
            )

    def reset_target_dir(self):
        """
        Reset the target pipeline directory. Check out the original branch.
        """
        log.info("Checking out original branch: '{}'".format(self.original_branch))
        try:
            self.repo.git.checkout(self.original_branch)
        except git.exc.GitCommandError as e:
            raise SyncException("Could not reset to original branch `{}`:\n{}".format(self.from_branch, e))
