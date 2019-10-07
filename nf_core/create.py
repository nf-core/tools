#!/usr/bin/env python
"""Creates a nf-core pipeline matching the current
organization's specification based on a template.
"""
import cookiecutter.main, cookiecutter.exceptions
import git
import logging
import os
import requests
import shutil
import sys
import tempfile

import nf_core


class PipelineCreate(object):
    """Creates a nf-core pipeline a la carte from the nf-core best-practise template.

    Args:
        name (str): Name for the pipeline.
        description (str): Description for the pipeline.
        author (str): Authors name of the pipeline.
        new_version (str): Version flag. Semantic versioning only. Defaults to `1.0dev`.
        no_git (bool): Prevents the creation of a local Git repository for the pipeline. Defaults to False.
        force (bool): Overwrites a given workflow directory with the same name. Defaults to False.
            May the force be with you.
        outdir (str): Path to the local output directory.
    """
    def __init__(self, name, description, author, new_version='1.0dev', no_git=False, force=False, outdir=None):
        self.short_name = name.lower().replace(r'/\s+/', '-').replace('nf-core/', '').replace('/', '-')
        self.name = 'nf-core/{}'.format(self.short_name)
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
        """Creates the nf-core pipeline.

        Launches cookiecutter, that will ask for required pipeline information.
        """

        # Make the new pipeline
        self.run_cookiecutter()

        # Init the git repository and make the first commit
        if not self.no_git:
            self.git_init_pipeline()

    def run_cookiecutter(self):
        """Runs cookiecutter to create a new nf-core pipeline.
        """
        logging.info("Creating new nf-core pipeline: {}".format(self.name))

        # Check if the output directory exists
        if os.path.exists(self.outdir):
            if self.force:
                logging.warning("Output directory '{}' exists - continuing as --force specified".format(self.outdir))
            else:
                logging.error("Output directory '{}' exists!".format(self.outdir))
                logging.info("Use -f / --force to overwrite existing files")
                sys.exit(1)
        else:
            os.makedirs(self.outdir)

        # Build the template in a temporary directory
        self.tmpdir = tempfile.mkdtemp()
        template = os.path.join(os.path.dirname(os.path.realpath(nf_core.__file__)), 'pipeline-template/')
        cookiecutter.main.cookiecutter(
            template,
            extra_context = {
                'name': self.name,
                'description': self.description,
                'author': self.author,
                'name_noslash': self.name_noslash,
                'name_docker': self.name_docker,
                'version': self.new_version,
                'nf_core_version': nf_core.__version__
            },
            no_input = True,
            overwrite_if_exists = self.force,
            output_dir = self.tmpdir
        )

        # Make a logo and save it
        self.make_pipeline_logo()

        # Move the template to the output directory
        for f in os.listdir(os.path.join(self.tmpdir, self.name_noslash)):
            shutil.move(os.path.join(self.tmpdir, self.name_noslash, f), self.outdir)

        # Delete the temporary directory
        shutil.rmtree(self.tmpdir)

    def make_pipeline_logo(self):
        """Fetch a logo for the new pipeline from the nf-core website
        """

        logo_url = "https://nf-co.re/logo/{}".format(self.short_name)
        logging.debug("Fetching logo from {}".format(logo_url))

        email_logo_path = "{}/{}/assets/{}_logo.png".format(self.tmpdir, self.name_noslash, self.name_noslash)
        logging.debug("Writing logo to {}".format(email_logo_path))
        r = requests.get("{}?w=400".format(logo_url))
        with open(email_logo_path, 'wb') as fh:
            fh.write(r.content)

        readme_logo_path = "{}/{}/docs/images/{}_logo.png".format(self.tmpdir, self.name_noslash, self.name_noslash)

        logging.debug("Writing logo to {}".format(readme_logo_path))
        if not os.path.exists(os.path.dirname(readme_logo_path)):
            os.makedirs(os.path.dirname(readme_logo_path))
        r = requests.get("{}?w=600".format(logo_url))
        with open(readme_logo_path, 'wb') as fh:
            fh.write(r.content)

    def git_init_pipeline(self):
        """Initialises the new pipeline as a Git repository and submits first commit.
        """
        logging.info("Initialising pipeline git repository")
        repo = git.Repo.init(self.outdir)
        repo.git.add(A=True)
        repo.index.commit("initial template build from nf-core/tools, version {}".format(nf_core.__version__))
        #Add TEMPLATE branch to git repository
        repo.git.branch('TEMPLATE')
        repo.git.branch('dev')
        logging.info("Done. Remember to add a remote and push to GitHub:\n  cd {}\n  git remote add origin git@github.com:USERNAME/REPO_NAME.git\n  git push --all origin".format(self.outdir))
        logging.info("This will also push your newly created dev branch and the TEMPLATE branch for syncing.")
