#!/usr/bin/env python
"""Bumps the version number in all appropriate files for
a nf-core pipeline.
"""

import git
import json
import logging
import nf_core
import os
import re
import requests
import shutil
import sys
import tempfile

class SyncException(Exception):
    """Exception raised when there was an error with TEMPLATE branch synchronisation
    """
    pass

class PullRequestException(Exception):
    """Exception raised when there was an error creating a Pull-Request on GitHub.com
    """
    pass

class PipelineSync(object):
    """Object to hold syncing information and results.

    Args:
        pipeline_dir (str): The path to the Nextflow pipeline root directory
        make_template_branch (bool): Set this to `True` to create a `TEMPLATE` branch if it is not found
        from_branch (str): The branch to use to fetch config vars. If not set, will use current active branch
        make_pr (bool): Set this to `True` to create a GitHub pull-request with the changes
        gh_username (str): GitHub username
        gh_repo (str): GitHub repository name
        gh_auth_token (str): Authorisation token used to make PR with GitHub API

    Attributes:
        pipeline_dir (str): Path to target pipeline directory
        from_branch (str): Repo branch to use when collecting workflow variables. Default: active branch.
        make_template_branch (bool): Whether to try to create TEMPLATE branch if not found
        orphan_branch (bool): Whether an orphan branch was made when creating TEMPLATE
        made_changes (bool): Whether making the new template pipeline introduced any changes
        make_pr (bool): Whether to try to automatically make a PR on GitHub.com
        required_config_vars (list): List of nextflow variables required to make template pipeline
        gh_username (str): GitHub username
        gh_repo (str): GitHub repository name
        gh_auth_token (str): Authorisation token used to make PR with GitHub API
    """

    def __init__(self, pipeline_dir, make_template_branch=False, from_branch=None, make_pr=False,
        gh_username=None, gh_repo=None, gh_auth_token=None):
        """ Initialise syncing object """

        self.pipeline_dir = os.path.abspath(pipeline_dir)
        self.from_branch = from_branch
        self.make_template_branch = make_template_branch
        self.orphan_branch = False
        self.made_changes = False
        self.make_pr = make_pr
        self.required_config_vars = [
            'manifest.name',
            'manifest.description',
            'manifest.version',
            'manifest.author'
        ]

        self.gh_username = gh_username
        self.gh_repo = gh_repo
        self.gh_auth_token = gh_auth_token
        if self.gh_auth_token is None:
            try:
                self.gh_auth_token = os.environ['NF_CORE_BOT']
            except KeyError:
                pass

    def sync(self):
        """ Find workflow attributes, create a new template pipeline on TEMPLATE
        """

        config_log_msg = "Pipeline directory: {}".format(self.pipeline_dir)
        if self.from_branch:
            config_log_msg += "\n  Using branch `{}` to fetch workflow variables".format(self.from_branch)
        if self.make_template_branch:
            config_log_msg += "\n  Will attempt to create `TEMPLATE` branch if not found"
        if self.make_pr:
            config_log_msg += "\n  Will attempt to automatically create a pull request on GitHub.com"
        logging.info(config_log_msg)

        self.inspect_sync_dir()

        self.get_wf_config()

        self.checkout_template_branch()

        self.make_template_pipeline()

        self.commit_template_changes()

        # Push and make a pull request if we've been asked to
        if self.make_pr:
            try:
                self.push_template_branch()
                self.make_pull_request()
            except PullRequestException as e:
                # Keep going - we want to clean up the target directory still
                logging.error(e)

        self.reset_target_dir()

        if not self.make_pr:
            self.git_merge_help()


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
        logging.debug("Original pipeline repository branch is '{}'".format(self.original_branch))

        # Check to see if there are uncommitted changes on current branch
        if self.repo.is_dirty(untracked_files=True):
            raise SyncException("Uncommitted changes found in pipeline directory!\nPlease commit these before running nf-core sync")

    def get_wf_config(self):
        """Check out the target branch if requested and fetch the nextflow config.
        Check that we have the required config variables.
        """
        # Try to check out target branch (eg. `origin/dev`)
        try:
            if self.from_branch and self.repo.active_branch.name != self.from_branch:
                logging.info("Checking out workflow branch '{}'".format(self.from_branch))
                self.repo.git.checkout(self.from_branch)
        except git.exc.GitCommandError:
            raise SyncException("Branch `{}` not found!".format(self.from_branch))

        # If not specified, get the name of the active branch
        if not self.from_branch:
            try:
                self.from_branch = self.repo.active_branch.name
            except git.exc.GitCommandError as e:
                logging.error("Could not find active repo branch: ".format(e))

        # Figure out the GitHub username and repo name from the 'origin' remote if we can
        try:
            gh_ssh_username_match = re.search(r'git@github\.com:([^\/]+)/([^\/]+)\.git$', self.repo.remotes.origin.url)
            if gh_ssh_username_match:
                self.gh_username = gh_ssh_username_match.group(1)
                self.gh_repo = gh_ssh_username_match.group(2)
            gh_url_username_match = re.search(r'https://github\.com/([^\/]+)/([^\/]+)\.git$', self.repo.remotes.origin.url)
            if gh_url_username_match:
                self.gh_username = gh_url_username_match.group(1)
                self.gh_repo = gh_url_username_match.group(2)
        except AttributeError as e:
            logging.debug("Could not find repository URL for remote called 'origin'")

        # Fetch workflow variables
        logging.info("Fetching workflow config variables")
        self.wf_config = nf_core.utils.fetch_wf_config(self.pipeline_dir)

        # Check that we have the required variables
        for rvar in self.required_config_vars:
            if rvar not in self.wf_config:
                raise SyncException("Workflow config variable `{}` not found!".format(rvar))

    def checkout_template_branch(self):
        """Try to check out the TEMPLATE branch. If it fails, try origin/TEMPLATE.
        If it still fails and --make-template-branch was given, create it as an orphan branch.
        """
        # Try to check out the `TEMPLATE` branch
        try:
            self.repo.git.checkout("origin/TEMPLATE", b="TEMPLATE")
        except git.exc.GitCommandError:

            # Try to check out an existing local branch called TEMPLATE
            try:
                self.repo.git.checkout("TEMPLATE")
            except git.exc.GitCommandError:

                # Failed, if we're not making a new branch just die
                if not self.make_template_branch:
                    raise SyncException(
                        "Could not check out branch 'origin/TEMPLATE'" \
                        "\nUse flag --make-template-branch to attempt to create this branch"
                    )

                # Branch and force is set, fire function to create `TEMPLATE` branch
                else:
                    logging.debug("Could not check out origin/TEMPLATE!")
                    logging.info("Creating orphan TEMPLATE branch")
                    try:
                        self.repo.git.checkout('--orphan', 'TEMPLATE')
                        self.orphan_branch = True
                        if self.make_pr:
                            self.make_pr = False
                            logging.warning("Will not attempt to make a PR - orphan branch must be merged manually first")
                    except git.exc.GitCommandError as e:
                        raise SyncException("Could not create 'TEMPLATE' branch:\n{}".format(e))

    def make_template_pipeline(self):
        """Delete all files and make a fresh template using the workflow variables
        """

        # Delete everything
        logging.info("Deleting all files in TEMPLATE branch")
        for the_file in os.listdir(self.pipeline_dir):
            if the_file == '.git':
                continue
            file_path = os.path.join(self.pipeline_dir, the_file)
            logging.debug("Deleting {}".format(file_path))
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                raise SyncException(e)

        # Make a new pipeline using nf_core.create
        logging.info("Making a new template pipeline using pipeline variables")

        # Suppress log messages from the pipeline creation method
        orig_loglevel = logging.getLogger().getEffectiveLevel()
        if orig_loglevel == getattr(logging, 'INFO'):
            logging.getLogger().setLevel(logging.ERROR)

        nf_core.create.PipelineCreate(
            name = self.wf_config['manifest.name'].strip('\"').strip("\'"),
            description = self.wf_config['manifest.description'].strip('\"').strip("\'"),
            new_version = self.wf_config['manifest.version'].strip('\"').strip("\'"),
            no_git = True,
            force = True,
            outdir = self.pipeline_dir,
            author = self.wf_config['manifest.author'].strip('\"').strip("\'"),
        ).init_pipeline()

        # Reset logging
        logging.getLogger().setLevel(orig_loglevel)

    def commit_template_changes(self):
        """If we have any changes with the new template files, make a git commit
        """
        # Commit changes if we have any
        if not self.repo.is_dirty(untracked_files=True):
            logging.info("Template contains no changes - no new commit created")
        else:
            try:
                self.repo.git.add(A=True)
                self.repo.index.commit("Template update for nf-core/tools version {}".format(nf_core.__version__))
                self.made_changes = True
                logging.info("Committed changes to TEMPLATE branch")
            except Exception as e:
                raise SyncException("Could not commit changes to TEMPLATE:\n{}".format(e))

    def push_template_branch(self):
        """If we made any changes, push the TEMPLATE branch to the default remote
        and try to make a PR. If we don't have the auth token, try to figure out a URL
        for the PR and print this to the console.
        """
        if self.made_changes:
            logging.info("Pushing TEMPLATE branch to remote")
            try:
                self.repo.git.push()
            except git.exc.GitCommandError as e:
                if self.make_template_branch:
                    try:
                        self.repo.git.push('--set-upstream', 'origin', 'TEMPLATE')
                    except git.exc.GitCommandError as e:
                        raise PullRequestException("Could not push TEMPLATE branch:\n  {}".format(e))
                else:
                    raise PullRequestException("Could not push TEMPLATE branch:\n  {}".format(e))
        else:
            logging.debug("No changes to TEMPLATE - skipping push to remote")

    def make_pull_request(self):
        """Create a pull request to a base branch (default: dev),
        from a head branch (default: TEMPLATE)

        Returns: An instance of class requests.Response
        """
        if not self.made_changes:
            logging.debug("No changes to TEMPLATE - skipping PR creation")

        # Check that we know the github username and repo name
        try:
            assert self.gh_username is not None
            assert self.gh_repo is not None
        except AssertionError:
            raise PullRequestException("Could not find GitHub username and repo from git remote 'origin'")

        # If we've been asked to make a PR, check that we have the credentials
        try:
            assert self.gh_auth_token is not None
        except AssertionError:
            logging.info("Make a PR at the following URL:\n  https://github.com/{}/{}/compare/{}...TEMPLATE".format(self.gh_username, self.gh_repo, self.original_branch))
            raise PullRequestException("No GitHub authentication token set - cannot make PR")

        logging.info("Submitting a pull request via the GitHub API")
        pr_content = {
            'title': "Important! Template update for nf-core/tools v{}".format(nf_core.__version__),
            'body': "Some important changes have been made in the nf-core/tools pipeline template. " \
                    "Please make sure to merge this pull-request as soon as possible. " \
                    "Once complete, make a new minor release of your pipeline.\n\n" \
                    "For more information, please see the [nf-core/tools v{tag} release page](https://github.com/nf-core/tools/releases/tag/{tag}).".format(tag=nf_core.__version__),
            'head': "TEMPLATE",
            'base': self.from_branch
        }
        r = requests.post(
            url = "https://api.github.com/repos/{}/{}/pulls".format(self.gh_username, self.gh_repo),
            data = json.dumps(pr_content),
            auth = requests.auth.HTTPBasicAuth(self.gh_username, self.gh_auth_token)
        )
        if r.status_code != 200:
            raise PullRequestException("GitHub API returned code {}: {}".format(r.status_code, r.text))
        logging.debug(r.json)

    def reset_target_dir(self):
        """Reset the target pipeline directory. Check out the original branch.
        """

        # Reset: Check out original branch again
        logging.debug("Checking out original branch: '{}'".format(self.original_branch))
        try:
            self.repo.git.checkout(self.original_branch)
        except git.exc.GitCommandError as e:
            raise SyncException("Could not reset to original branch `{}`:\n{}".format(self.from_branch, e))

    def git_merge_help(self):
        """Print a command line help message with instructions on how to merge changes
        """
        if self.made_changes:
            git_merge_cmd = 'git merge TEMPLATE'
            manual_sync_link = ''
            if self.orphan_branch:
                git_merge_cmd += ' --allow-unrelated-histories'
                manual_sync_link = "\n\nFor more information, please see:\nhttps://nf-co.re/developers/sync#merge-template-into-main-branches"
            logging.info(
                "Now try to merge the updates in to your pipeline:\n  cd {}\n  {}{}".format(
                    self.pipeline_dir,
                    git_merge_cmd,
                    manual_sync_link
                )
            )
