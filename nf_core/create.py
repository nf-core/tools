#!/usr/bin/env python
""" Release code for the nf-core python package.

Creates a nf-core pipeline matching the current
organization's specification.
"""

import cookiecutter.main, cookiecutter.exceptions
import git
import logging
import os
import shutil
import sys
import tempfile

import nf_core

class PipelineCreate(object):
    """ Object to create a new pipeline """

    def __init__(self, name, description, author, new_version='1.0dev', no_git=False, force=False, outdir=None):
        """ Init the object and define variables """
        self.name = 'nf-core/{}'.format(
            name.lower().replace(r'/\s+/', '-').replace('nf-core/', '').replace('/', '-')
        )
        self.name_noslash = self.name.replace('/', '-')
        self.name_docker = self.name.replace('nf-core', 'nfcore')
        self.description = description
        self.author = author
        self.new_version = new_version
        self.no_git = no_git
        self.force = force
        self.outdir = outdir
        if not self.outdir:
            self.outdir = os.path.join(os.getcwd(), self.name_noslash)

    def init_pipeline(self):
        """Function to init a new pipeline. Called by the main cli"""

        # Make the new pipeline
        self.run_cookiecutter()

        # Init the git repository and make the first commit
        if not self.no_git:
            self.git_init_pipeline()

    def run_cookiecutter(self):
        """Run cookiecutter to create a new pipeline"""

        logging.info("Creating new nf-core pipeline: {}".format(self.name))

        # Check if the output directory exists
        if os.path.exists(self.outdir):
            if self.force:
                logging.warn("Output directory '{}' exists - continuing as --force specified".format(self.outdir))
            else:
                logging.error("Output directory '{}' exists!".format(self.outdir))
                logging.info("Use -f / --force to overwrite existing files")
                sys.exit(1)
        else:
            os.makedirs(self.outdir)

        # Build the template in a temporary directory
        tmpdir = tempfile.mkdtemp()
        template = os.path.join(os.path.dirname(os.path.realpath(nf_core.__file__)), 'pipeline-template/')
        cookiecutter.main.cookiecutter (
            template,
            extra_context = {
                'name':self.name,
                'description':self.description,
                'author':self.author,
                'name_noslash':self.name_noslash,
                'name_docker':self.name_docker,
                'version':self.new_version
            },
            no_input = True,
            overwrite_if_exists = self.force,
            output_dir = tmpdir
        )

        # Move the template to the output directory
        for f in os.listdir(os.path.join(tmpdir, self.name_noslash)):
            shutil.move(os.path.join(tmpdir, self.name_noslash, f), self.outdir)

        # Delete the temporary directory
        shutil.rmtree(tmpdir)


    def git_init_pipeline(self):
        """Initialise the new pipeline as a git repo and make first commit"""
        logging.info("Initialising pipeline git repository")
        repo = git.Repo.init(self.outdir)
        repo.git.add(A=True)
        repo.index.commit("initial template build from nf-core/tools, version {}".format(nf_core.__version__))
        logging.info("Done. Remember to add a remote and push to GitHub:\n  cd {}\n  git remote add origin git@github.com:USERNAME/REPO_NAME.git\n  git push".format(self.outdir))
