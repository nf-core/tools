#!/usr/bin/env python
""" Download a nf-core pipeline """

from __future__ import print_function

from io import BytesIO
import logging
import os
import requests
import subprocess
import sys
from zipfile import ZipFile


import nf_core.list, nf_core.lint

def download_workflow(pipeline, release=None, singularity=False, outdir=None):
    """ Main function to download a nf-core workflow """

    # init
    wf = DownloadWorkflow(pipeline, release, singularity, outdir)

    # Get workflow details
    if not wf.get_workflow():
        sys.exit(1)

    # Check that the outdir doesn't already exist
    if os.path.exists(wf.outdir):
        logging.error("Output directory '{}' already exists".format(wf.outdir))
        sys.exit(1)
    else:
        logging.info("Saving nf-core/{} to '{}'".format(wf.wf_name, wf.outdir))

    # Download the pipeline files
    logging.info("Downloading workflow files from GitHub")
    wf.download_wf_files()

    # Download the singularity images
    if singularity:
        logging.info("Fetching container names for workflow")
        wf.find_singularity_images()
        if len(wf.containers) == 0:
            logging.info("No container names found in workflow")
        else:
            os.mkdir(os.path.join(wf.outdir, 'singularity-images'))
            for container in wf.containers:
                wf.download_singularity_image(container)

class DownloadWorkflow():

    def __init__(self, pipeline, release=None, singularity=False, outdir=None):
        """ Set class variables """

        self.pipeline = pipeline
        self.release = release
        self.singularity = singularity
        self.outdir = outdir

        self.wf_name = None
        self.wf_sha = None
        self.wf_download_url = None
        self.containers = list()


    def get_workflow(self):
        """ Fetch details of nf-core workflow to download """
        wfs = nf_core.list.Workflows()
        wfs.get_remote_workflows()

        # Get workflow download details
        for wf in wfs.remote_workflows:
            if wf.full_name == self.pipeline or wf.name == self.pipeline:

                # Set pipeline name
                self.wf_name = wf.name

                # Find latest release hash
                if self.release is None and len(wf.releases) > 0:
                    self.release = wf.releases[0]['tag_name']
                    self.wf_sha = wf.releases[0]['tag_sha']
                # Find specified release hash
                elif self.release is not None:
                    for r in wf.releases:
                        if r['tag_name'] == self.release.lstrip('v'):
                            self.wf_sha = r['tag_sha']
                            break
                    else:
                        logging.error("Not able to find release '{}' for {} (found '{}')".format(self.release, wf.full_name, "', '".join([r['tag_name'] for r in wf.releases])))
                        return False
                # Must be a dev-only pipeline
                elif self.release is None:
                    self.release = 'dev'
                    self.wf_sha = 'master' # Cheating a little, but GitHub download link works

                # Set outdir name if not defined
                if self.outdir is None:
                    self.outdir = 'nf-core-{}'.format(wf.name)
                    if self.release is not None:
                        self.outdir += '-{}'.format(self.release)

                # Set the download URL
                self.wf_download_url = 'https://github.com/{}/archive/{}.zip'.format(wf.full_name, self.wf_sha)

                # Finished
                return True

        # If we got this far, must have not found the pipeline
        logging.error("Not able to find pipeline '{}'".format(self.pipeline))
        logging.info("Available pipelines: {}".format(', '.join([w.name for w in wfs.remote_workflows])))
        return False

    def download_wf_files(self):
        """ Download workflow files from GitHub - save in outdir """

        # Download GitHub zip file into memory and extract
        url = requests.get(self.wf_download_url)
        zipfile = ZipFile(BytesIO(url.content))
        zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        gh_name = '{}-{}'.format(self.wf_name, self.wf_sha)
        os.rename(os.path.join(self.outdir, gh_name), os.path.join(self.outdir, 'workflow'))

    def find_singularity_images(self):
        """ Find singularity image names for workflow """

        # Use linting code to parse the pipeline nextflow config
        lint_obj = nf_core.lint.PipelineLint(os.path.join(self.outdir, 'workflow'))
        lint_obj.check_nextflow_config()

        # Find any config variables that look like a container
        for k,v in lint_obj.config.items():
            if k.startswith('process.') and k.endswith('.container'):
                self.containers.append(v.strip('"').strip("'"))

    def download_singularity_image(self, container):
        """ Download singularity images for workflow """

        out_name = '{}.simg'.format(container.replace('nfcore/', 'nf-core-').replace(':', '-'))
        out_path = os.path.abspath(os.path.join(self.outdir, 'singularity-images', out_name))
        address = 'docker://{}'.format(container.replace('docker://', ''))
        singularity_command = ["singularity", "pull", "--name", out_path, address]
        docker_command = [
            'docker', 'run',
            '-v', '/var/run/docker.sock:/var/run/docker.sock',
            '-v', '{}:/output'.format(out_path),
            '--privileged', '-t', '--rm',
            'singularityware/docker2singularity',
            container
        ]

        logging.info("Building singularity image '{}', saving to {}".format(container, out_path))

        # Try to use singularity to pull image
        try:
            subprocess.call(singularity_command)
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                # Singularity is not installed
                logging.warn('Singularity is not installed. Attempting to use Docker instead.')

                # Try to use docker to use singularity to pull image
                try:
                    subprocess.call(docker_command)
                except OSError as e:
                    if e.errno == os.errno.ENOENT:
                        # Docker is not installed
                        logging.warn('Docker is not installed.')
                    else:
                        # Something else went wrong with docker command
                        raise
            else:
                # Something else went wrong with singularity command
                raise
