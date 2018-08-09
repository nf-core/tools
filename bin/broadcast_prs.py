#!/usr/bin/env python

from cookiecutter.main import cookiecutter
import git
import json
import os
import requests
from requests.auth import HTTPBasicAuth
import shutil
import sys
import subprocess
import tempfile
import utils

# The GitHub base url or the nf-core project
GH_BASE_URL = "https://{token}@github.com/nf-core"
# The current cookiecutter template url for nf-core pipelines
NF_CORE_TEMPLATE = os.path.join(
                        os.path.dirname(
                                os.path.dirname(os.path.realpath(__file__))
                        ), "nf_core/pipeline-template")
# The JSON file is updated on every push event on the nf-core GitHub project
NF_CORE_PIPELINE_INFO = "http://nf-co.re/pipelines.json"
# The API endpoint for creating pull requests
GITHUB_PR_URL_TEMPL = "https://api.github.com/repos/nf-core/{pipeline}/pulls"


class UpdateTemplate:
    """Updates the template content of an nf-core pipeline in
    its `TEMPLATE` branch.

    Args: - pipeline: The pipeline name
          - branch: The template branch name, default=`TEMPLATE`
          - token: GitHub auth token
    """

    def __init__(self, pipeline, branch='TEMPLATE', token=""):
        """Basic constructor
        """
        self.pipeline = pipeline
        self.repo_url = "{base_url}/{pipeline}".format(
                    base_url=GH_BASE_URL.format(token=token),
                    pipeline=pipeline)
        self.branch = branch
        self.tmpdir = tempfile.mkdtemp()
        self.templatedir = tempfile.mkdtemp()
        self.repo = None
    
    def run(self):
        """Execute the template update.
        """
        config = self._clone_repo()
        assert self.repo
        context = utils.create_context(config)
        self._apply_changes(context)
        self._commit_changes()
        self._push_changes()

    def _clone_repo(self):
        """Clone the repo and switch to the configured branch.
        """
        self.repo = git.Repo.clone_from(self.repo_url, self.tmpdir)
        config = utils.fetch_wf_config(wf_path=self.tmpdir)
        self.repo.git.checkout("origin/{branch}".format(branch=self.branch),
            b="{branch}".format(branch=self.branch))
        return config

    def _apply_changes(self, context):
        """Apply the changes of the cookiecutter template
        to the pipelines template branch.
        """
        cookiecutter(NF_CORE_TEMPLATE,
                     no_input=True,
                     extra_context=context,
                     overwrite_if_exists=True,
                     output_dir=self.templatedir)
        # Clear the template branch content
        for f in os.listdir(self.tmpdir):
            if f == ".git": continue
            try:
                shutil.rmtree(os.path.join(self.tmpdir, f))
            except:
                os.remove(os.path.join(self.tmpdir, f))
        # Move the new template content into the template branch
        template_path = os.path.join(self.templatedir, self.pipeline)
        for f in os.listdir(template_path):
            shutil.move(
                os.path.join(template_path, f), # src
                os.path.join(self.tmpdir, f), # dest
            )

    def _commit_changes(self):
        """Commits the changes of the new template to the current branch.
        """
        self.repo.git.add(A=True)
        self.repo.index.commit("Update nf-core pipeline template.")

    def _push_changes(self):
        self.repo.git.push()
        

def create_pullrequest(pipeline, origin="dev", template="TEMPLATE", token="", user="nf-core"):
    """Create a pull request to a base branch (default: dev),
    from a head branch (default: TEMPLATE)

    Returns: An instance of class requests.Response
    """
    content = {}
    content['title'] = "Important pipeline nf-core update! (version {tag})".format(tag=os.environ['TRAVIS_TAG'])
    content['body'] = "Some important changes have been made in the nf-core pipelines templates.\n" \
    "Please make sure to merge this in ASAP and make a new minor release of your pipeline.\n\n" \
    "Follow the link [nf-core/tools](https://github.com/nf-core/tools/releases/tag/{})".format(os.environ['TRAVIS_TAG'])
    content['head'] = "{}".format(template)
    content['base'] = origin
    return requests.post(url=GITHUB_PR_URL_TEMPL.format(pipeline=pipeline),
                         data=json.dumps(content),
                         auth=HTTPBasicAuth(user, token))

def main():
    # Check that the commit event is a GitHub tag event
    assert os.environ['TRAVIS_TAG']
    assert os.environ['NF_CORE_BOT']
    # Get nf-core pipelines info
    res = requests.get(NF_CORE_PIPELINE_INFO)
    pipelines = json.loads(res.content).get('remote_workflows')
    if not pipelines:
        print("Pipeline information was empty!")
    
    # TODO: Remove this line, once we go for production
    pipelines = [{"name":"hlatyping"}] # just for testing
    
    # Update the template branch of each pipeline repo
    for pipeline in pipelines:
        print("Update template branch for pipeline '{pipeline}'... ".format(pipeline=pipeline['name']))
        UpdateTemplate(pipeline['name'], token=os.environ['NF_CORE_BOT']).run()
    
    # Create a pull request from each template branch to the origin branch
    for pipeline in pipelines:
        print("Trying to open pull request for pipeline {}...".format(pipeline['name']))
        response = create_pullrequest(pipeline['name'], token=os.environ["NF_CORE_BOT"])
        if response.status_code != 201:
            print("Pull-request for pipeline \'{pipeline}\' failed," 
            " got return code {return_code}."
            .format(pipeline=pipeline["name"], return_code=response.status_code))
            print(response.content)
        else:
            print("Created pull-request for pipeline \'{pipeline}\' successfully."
                .format(pipeline=pipeline["name"]))
            
if __name__ == "__main__":
    main()

