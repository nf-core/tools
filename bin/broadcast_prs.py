#!/usr/bin/env python

import os
import sys
import subprocess
from cookiecutter.main import cookiecutter
import requests
from requests.auth import HTTPBasicAuth
import json

GH_BASE_URL = "https://github.com/nf-core"
NF_CORE_TEMPLATE = "https://github.com/nf-core/cookiecutter.git"
# The JSON file is updated on every push event on the nf-core GitHub
# project
NF_CORE_PIPELINE_INFO = "http://nf-co.re/pipelines.json"
GITHUB_PR_URL_TEMPL = "https://api.github.com/repos/nf-core/{pipeline}/pulls"


class UpdateTemplate:
    """Updates the template content of an nf-core pipeline in
    its `TEMPLATE` branch.

    Args: - pipeline: The pipeline name
          - context: a parsed dictionary of a cookiecutter.json file
          - branch: The template branch name, default=`TEMPLATE`
    """

    def __init__(self, pipeline, context, branch='TEMPLATE'):
        """Basic constructor
        """
        self.pipeline = pipeline
        self.repo_url = "{base_url}/{pipeline}".format(
                    base_url=GH_BASE_URL,
                    pipeline=pipeline)
        self.context = context
        self.branch = branch

    
    def run(self):
        """Execute the template update.
        """
        self._clone_repo()
        self._apply_changes()
        self._commit_changes()
    
    def _clone_repo(self):
        """Clone the repo and switch to the configured branch.
        """
        subprocess.run(["git", "clone", self.repo_url, "-b", self.branch, self.pipeline])

    def _apply_changes(self):
        """Apply the changes of the cookiecutter template
        to the pipelines template branch.
        """
        cookiecutter(NF_CORE_TEMPLATE,
                     no_input=True,
                     extra_context=None,
                     overwrite_if_exists=True,
                     output_dir=self.pipeline)
    
    def _commit_changes(self):
        """Commits the changes of the new template to the current branch.
        """
        subprocess.run(["git", "add", "-A", "."], cwd=self.pipeline)
        subprocess.run(["git", "commit", "-m", "Update nf-core template"], cwd=self.pipeline)
        

def create_pullrequest(pipeline, origin="master", template="TEMPLATE", token="", user="nf-core"):
    """Create a pull request to a base branch (default: master),
    from a head branch (default: TEMPLATE)

    Returns: An instance of class requests.Response
    """
    content = {}
    content['title'] = "Important pipeline nf-core update!"
    content['body'] = "Some important changes have been made in the nf-core pipelines templates.\n" +
    "Please make sure to merge this in ASAP and make a new minor release of your pipeline."
    content['head'] = "{}:{}".format(pipeline, template)
    content['base'] = master
    return requests.post(url=GITHUB_PR_URL_TEMPL.format(pipeline=pipeline),
                         data=json.dumps(content)
                         auth=HTTPBasicAuth(user, token))

def get_context(pipeline):
    """Get the template context for a given pipeline.
    
    Returns: A context dictionary
    """
    pass

def main():
    res = requests.get(NF_CORE_PIPELINE_INFO)
    pipelines = json.loads(res.content).get('remote_workflows')
    if not pipelines:
        print("Pipeline information was empty!")
    for pipeline in pipelines:
        # Get context from pipeline and load it into a dictionary
        # context = load_context(pipeline)
        print(pipeline['name']) # Just for testing, can be safely deleted
        ut.UpdateTemplate(pipeline['name'], context)
    
    for pipeline in pipelines:
        print("Trying to open pull request for pipeline {}...".format(pipeline['name']))
        response = create_pullrequest(pipeline['name'])
        if response.status_code != 201:
            print("Pull-request for pipeline \'{pipeline}\' failed," 
            " got return code {return_code}."
            .format(pipeline=pipeline, return_code=response.status_code))
        else:
            print("Created pull-request for pipeline \'{pipeline}\' successfully.".format(pipeline=pipeline))
            
if __name__ == "__main__":
    main()

