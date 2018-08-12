#!/usr/bin/env python
""" Release code for the nf-core python package.

Bumps the version number in all appropriate files for
a nf-core pipeline
"""

import cookiecutter.main, cookiecutter.exceptions
import git
import logging
import os
import re

import nf_core

def init_pipeline(name, description, new_version='1.0dev', no_git=False, force=False):
    """Function to init a new pipeline. Called by the main cli"""

    # Make the new pipeline
    run_cookiecutter(name, description, new_version, force)

    # Init the git repository and make the first commit
    if not no_git:
        git_init_pipeline(name)

def run_cookiecutter(name, description, new_version='1.0dev', force=False):
    """Run cookiecutter to create a new pipeline"""

    logging.info("Creating new nf-core pipeline: {}".format(name))
    template = os.path.join(os.path.dirname(os.path.realpath(nf_core.__file__)), 'pipeline-template/')
    try:
        cookiecutter.main.cookiecutter (
            template,
            extra_context={'pipeline_name':name, 'pipeline_short_description':description, 'version':new_version},
            no_input=True,
            overwrite_if_exists=force
        )
    except (cookiecutter.exceptions.OutputDirExistsException) as e:
        logging.error(e)
        logging.info("Use -f / --force to overwrite existing files")

def git_init_pipeline(name):
    """Initialise the new pipeline as a git repo and make first commit"""
    logging.info("Initialising pipeline git repository")
    pipeline_dir = os.path.join(os.getcwd(), name)
    repo = git.Repo.init(pipeline_dir)
    repo.git.add(A=True)
    repo.index.commit("initial commit")
    logging.info("Done. Remember to add a remote and push to GitHub!")
