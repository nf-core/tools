#!/usr/bin/env python
"""Bumps the version number in all appropriate files for
a nf-core pipeline.
"""

import git
import json
import logging
import nf_core
import os
import requests
import shutil
import sys
import tempfile

class PipelineSync(object):
    """Object to hold syncing information and results.

    Args:
        pipeline_dir (str): The path to the Nextflow pipeline root directory
        make_template_branch (bool): Set this to `True` to create a `TEMPLATE` branch if it is not found
        from_branch (str): The branch to use to fetch config vars. If not set, will use current active branch
        make_pr (bool): Set this to `True` to create a GitHub pull-request with the changes

    Attributes:
        gh_base_url (str): The GitHub base url or the nf-core project
        github_pr_url_templ (str): The API endpoint for creating pull requests
        path_parent_dir (str): Current script directory
        sync_errors (list): List of errors from sync
        pr_errors (list): List of errors from PR
    """

    def __init__(self, pipeline_dir, make_template_branch=False, from_branch=None, make_pr=False):
        """ Initialise syncing object """

        self.pipeline_dir = os.path.abspath(pipeline_dir)
        self.make_template_branch = make_template_branch
        self.from_branch = from_branch
        self.orphan_branch = False
        self.make_pr = make_pr

        self.gh_base_url = "https://{token}@github.com/nf-core/{pipeline}"
        self.github_pr_url_templ = "https://api.github.com/repos/nf-core/{pipeline}/pulls"

        self.sync_error = False
        self.pr_error = False

    def sync(self):
        """ Find workflow attributes, create a new template pipeline on TEMPLATE
        """

        logging.info("Pipeline directory: {}".format(self.pipeline_dir))

        # Check that the pipeline_dir is a git repo
        try:
            self.repo = git.Repo(self.pipeline_dir)
        except git.exc.InvalidGitRepositoryError as e:
            self.sync_error = True
            logging.error("'{}' does not appear to be a git repository".format(self.pipeline_dir))
            return False

        # If we've been asked to make a PR, check that we have the credentials
        if self.make_pr:
            try:
                assert length(str(os.environ['NF_CORE_BOT'])) > 5
            except (IndexError, AssertionError) as e:
                self.sync_error = True
                logging.error("Environment variable `$NF_CORE_BOT` is not set - cannot make PR")
                return False


        # get current branch so we can switch back later
        self.original_branch = self.repo.active_branch.name
        logging.debug("Original pipeline repository branch is '{}'".format(self.original_branch))

        # Check to see if there are uncommitted changes on current branch
        if self.repo.is_dirty(untracked_files=True):
            self.sync_error = True
            logging.error("Uncommitted changes found in pipeline directory!\nPlease commit these before running nf-core sync")
            return False

        # Try to check out target branch (eg. `origin/dev`)
        try:
            if self.from_branch and self.repo.active_branch.name != self.from_branch:
                logging.info("Checking out workflow branch '{}'".format(self.from_branch))
                self.repo.git.checkout(self.from_branch)
        except git.exc.GitCommandError:
            self.sync_error = True
            logging.error("Branch `{}` not found!".format(self.from_branch))
            return False

        # Fetch workflow variables
        logging.info("Fetching workflow config variables")
        self.wf_config = nf_core.utils.fetch_wf_config(self.pipeline_dir)

        # Check that we have the required variables
        for rvar in ['manifest.name','manifest.description','manifest.version','manifest.author']:
            if rvar not in self.wf_config:
                self.sync_error = True
                logging.error("Workflow config variable `{}` not found!".format(rvar))
                return False


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
                    self.sync_error = True
                    logging.error("Could not check out branch 'origin/TEMPLATE'")
                    return False

                # Branch and force is set, fire function to create `TEMPLATE` branch
                else:
                    logging.debug("Could not check out origin/TEMPLATE!")
                    logging.info("Creating orphan TEMPLATE branch")
                    try:
                        self.repo.git.checkout('--orphan', 'TEMPLATE')
                        self.orphan_branch = True
                    except git.exc.GitCommandError as e:
                        self.sync_error = True
                        logging.error("Could not create 'TEMPLATE' branch:\n{}".format(e))
                        return False

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
                self.sync_error = True
                logging.error(e)
                return False

        # Make a new pipeline using nf_core.create
        logging.info("Making a new template pipeline using pipeline variables")
        nf_core.create.PipelineCreate(
            name = self.wf_config['manifest.name'],
            description = self.wf_config['manifest.description'],
            new_version = self.wf_config['manifest.version'],
            no_git = True,
            force = True,
            outdir = self.pipeline_dir,
            author = self.wf_config['manifest.author'],
        ).init_pipeline()

        # Commit changes if we have any
        if not self.repo.is_dirty(untracked_files=True):
            logging.info("Template contains no changes - no new commit created")
        else:
            try:
                self.repo.git.add(A=True)
                self.repo.index.commit("Template update for nf-core/tools version {}".format(nf_core.__version__))
            except Exception as e:
                self.sync_error = True
                logging.error("Could not commit changes to TEMPLATE:\n{}".format(e))
                return False

        # Push and make a pull request if we've been asked to
        if self.make_pr:
            self.repo.git.push()
            #
            # TODO - MAKE PR
            #
            #
            #
            #

        # Reset: Check out original branch again
        logging.debug("Checking out original branch: '{}'".format(self.original_branch))
        try:
            self.repo.git.checkout(self.original_branch)
        except git.exc.GitCommandError as e:
            self.sync_error = True
            logging.error("Could not reset to original branch `{}`:\n{}".format(self.from_branch, e))
            return False

        # Finish up
        if not self.make_pr:
            git_merge_cmd = 'git merge TEMPLATE'
            if self.orphan_branch:
                git_merge_cmd += ' --allow-unrelated-histories'
            logging.info("Now try to merge the updates in to your pipeline:\n  {}".format(git_merge_cmd))



#    def update_template_branch(self):
#        """ Check out `TEMPLATE` and make a new pipeline using nf_core.create """
#
#        try:
#            syncutils.template.NfcoreTemplate(
#                pipeline['name'],
#                branch=DEF_TEMPLATE_BRANCH,
#                repo_url=GH_BASE_URL.format(token=os.environ["NF_CORE_BOT"], pipeline=pipeline['name'])
#            ).sync()
#        except Exception as e:
#            sync_errors.append((pipeline['name'], e))
#
#    def create_pull_request(self):
#        name = pipeline.get('name')
#        for errored_pipeline, _ in sync_errors:
#            if name == errored_pipeline:
#                return
#        response = create_pullrequest(name, token=os.environ["NF_CORE_BOT"])
#        if response.status_code != 201:
#            pr_errors.append((name, response.status_code, response.content))
#        else:
#            print("Created pull-request for pipeline \'{pipeline}\' successfully."
#                  .format(pipeline=name))
#
#
#
#
#
#
#def create_pullrequest(pipeline, origin="dev", template="TEMPLATE", token="", user="nf-core"):
#    """Create a pull request to a base branch (default: dev),
#    from a head branch (default: TEMPLATE)
#
#    Returns: An instance of class requests.Response
#    """
#    content = {}
#    content['title'] = "Important pipeline nf-core update! (version {tag})".format(tag=os.environ['TRAVIS_TAG'])
#    content['body'] = "Some important changes have been made in the nf-core pipelines templates.\n" \
#    "Please make sure to merge this in ASAP and make a new minor release of your pipeline.\n\n" \
#    "Follow the link [nf-core/tools](https://github.com/nf-core/tools/releases/tag/{})".format(os.environ['TRAVIS_TAG'])
#    content['head'] = "{}".format(template)
#    content['base'] = origin
#    return requests.post(url=GITHUB_PR_URL_TEMPL.format(pipeline=pipeline),
#                         data=json.dumps(content),
#                         auth=requests.auth.TTPBasicAuth(user, token))
#
#
#def filter_blacklisted_pipelines_from_list(pipelines, blacklisted_pipelines):
#    filtered_pipelines = []
#    for pipeline in pipelines:
#        if not pipeline.get('name'):
#            print("No attribute \'name\' for pipeline found: {}".format(pipeline))
#        else:
#            filtered_pipelines.append(pipeline) if pipeline.get('name') not in blacklisted_pipelines \
#                else filtered_pipelines
#    return filtered_pipelines
#
#
#def fetch_black_listed_pipelines_from_file(file_path):
#    with open(file_path) as fh:
#        blacklist = json.load(fh)
#    return blacklist.get('pipelines')
#
#
#def fetch_nfcore_workflows_from_website(url):
#    try:
#        res = requests.get(url)
#        pipelines = res.json().get('remote_workflows')
#    except Exception as e:
#        print("Could not get remote workflows. Reason was: {}".format(e))
#        pipelines = []
#    return pipelines
#
#
#def update_template_branch_for_pipeline(pipeline):
#    try:
#        syncutils.template.NfcoreTemplate(
#            pipeline['name'],
#            branch=DEF_TEMPLATE_BRANCH,
#            repo_url=GH_BASE_URL.format(token=os.environ["NF_CORE_BOT"], pipeline=pipeline['name'])
#        ).sync()
#    except Exception as e:
#        sync_errors.append((pipeline['name'], e))
#
#
#def create_pullrequest_if_update_sucessful(pipeline):
#    name = pipeline.get('name')
#    for errored_pipeline, _ in sync_errors:
#        if name == errored_pipeline:
#            return
#    response = create_pullrequest(name, token=os.environ["NF_CORE_BOT"])
#    if response.status_code != 201:
#        pr_errors.append((name, response.status_code, response.content))
#    else:
#        print("Created pull-request for pipeline \'{pipeline}\' successfully."
#              .format(pipeline=name))
#
#
#def main():
#    assert os.environ['TRAVIS_TAG']
#    assert os.environ['NF_CORE_BOT']
#
#    blacklisted_pipeline_names = fetch_black_listed_pipelines_from_file(PATH_PARENT_DIR + "/blacklist.json")
#
#    pipelines = fetch_nfcore_workflows_from_website(NF_CORE_PIPELINE_INFO)
#
#    if len(sys.argv) > 1:
#        pipeline_to_sync = sys.argv[1]
#        filtered_pipelines = [pipeline for pipeline in pipelines if pipeline_to_sync in pipeline.get('name')]
#    else:
#        filtered_pipelines = filter_blacklisted_pipelines_from_list(pipelines, blacklisted_pipeline_names)
#
#    for pipeline in filtered_pipelines:
#        print("Update template branch for pipeline '{pipeline}'... ".format(pipeline=pipeline['name']))
#        update_template_branch_for_pipeline(pipeline)
#        print("Trying to open pull request for pipeline {}...".format(pipeline['name']))
#        create_pullrequest_if_update_sucessful(pipeline)
#
#    for pipeline, exception in sync_errors:
#        print("WARNING!!!! Sync for pipeline {name} failed.".format(name=pipeline))
#        print(exception)
#
#    for pipeline, return_code, content in pr_errors:
#        print("WARNING!!!! Pull-request for pipeline \'{pipeline}\' failed,"
#              " got return code {return_code}."
#              .format(pipeline=pipeline, return_code=return_code))
#        print(content)
#
#    sys.exit(0)
