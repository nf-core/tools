#!/usr/bin/env python
"""Downloads a nf-core pipeline to the local file system."""

from __future__ import print_function

from io import BytesIO
import click
import logging
import hashlib
import os
import requests
import requests_cache
import subprocess
import sys
from zipfile import ZipFile

import nf_core.list
import nf_core.utils


class DownloadWorkflow(object):
    """Downloads a nf-core workflow from Github to the local file system.

    Can also download its Singularity container image if required.

    Args:
        pipeline (str): A nf-core pipeline name.
        release (str): The workflow release version to download, like `1.0`. Defaults to None.
        singularity (bool): Flag, if the Singularity container should be downloaded as well. Defaults to False.
        outdir (str): Path to the local download directory. Defaults to None.
    """
    def __init__(self, pipeline, release=None, singularity=False, outdir=None):
        self.pipeline = pipeline
        self.release = release
        self.singularity = singularity
        self.outdir = outdir

        self.wf_name = None
        self.wf_sha = None
        self.wf_download_url = None
        self.config = dict()
        self.containers = list()

    def download_workflow(self):
        """Starts a nf-core workflow download."""
        # Get workflow details
        try:
            self.fetch_workflow_details(nf_core.list.Workflows())
        except LookupError:
            sys.exit(1)

        # Check that the outdir doesn't already exist
        if os.path.exists(self.outdir):
            logging.error("Output directory '{}' already exists".format(self.outdir))
            sys.exit(1)

        logging.info(
            "Saving {}".format(self.pipeline) +
            "\n Pipeline release: {}".format(self.release) +
            "\n Pull singularity containers: {}".format('Yes' if self.singularity else 'No') +
            "\n Output directory: {}".format(self.outdir)
        )

        # Download the pipeline files
        logging.info("Downloading workflow files from GitHub")
        self.download_wf_files()

        # Download the singularity images
        if self.singularity:
            logging.debug("Fetching container names for workflow")
            self.find_container_images()
            if len(self.containers) == 0:
                logging.info("No container names found in workflow")
            else:
                os.mkdir(os.path.join(self.outdir, 'singularity-images'))
                logging.info("Downloading {} singularity container{}".format(len(self.containers), 's' if len(self.containers) > 1 else ''))
                for container in self.containers:
                    try:
                        # Download from Dockerhub in all cases
                        self.pull_singularity_image(container)
                    except RuntimeWarning as r:
                        # Raise exception if this is not possible
                        logging.error("Not able to pull image. Service might be down or internet connection is dead.")
                        raise r

                        

    def fetch_workflow_details(self, wfs):
        """Fetches details of a nf-core workflow to download.

        Args:
            wfs (nf_core.list.Workflows): A nf_core.list.Workflows object

        Raises:
            LockupError, if the pipeline can not be found.
        """
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
                    logging.debug("No release specified. Using latest release: {}".format(self.release))
                # Find specified release hash
                elif self.release is not None:
                    for r in wf.releases:
                        if r['tag_name'] == self.release.lstrip('v'):
                            self.wf_sha = r['tag_sha']
                            break
                    else:
                        logging.error("Not able to find release '{}' for {}".format(self.release, wf.full_name))
                        logging.info("Available {} releases: {}".format(wf.full_name, ', '.join([r['tag_name'] for r in wf.releases])))
                        raise LookupError("Not able to find release '{}' for {}".format(self.release, wf.full_name))

                # Must be a dev-only pipeline
                elif not self.release:
                    self.release = 'dev'
                    self.wf_sha = 'master' # Cheating a little, but GitHub download link works
                    logging.warn("Pipeline is in development - downloading current code on master branch.\n" +
                        "This is likely to change soon should not be considered fully reproducible.")

                # Set outdir name if not defined
                if not self.outdir:
                    self.outdir = 'nf-core-{}'.format(wf.name)
                    if self.release is not None:
                        self.outdir += '-{}'.format(self.release)

                # Set the download URL and return
                self.wf_download_url = 'https://github.com/{}/archive/{}.zip'.format(wf.full_name, self.wf_sha)
                return

        # If we got this far, must not be a nf-core pipeline
        if self.pipeline.count('/') == 1:
            # Looks like a GitHub address - try working with this repo
            logging.warn("Pipeline name doesn't match any nf-core workflows")
            logging.info("Pipeline name looks like a GitHub address - attempting to download anyway")
            self.wf_name = self.pipeline
            if not self.release:
                self.release = 'master'
            self.wf_sha = self.release
            if not self.outdir:
                self.outdir = self.pipeline.replace('/', '-').lower()
                if self.release is not None:
                    self.outdir += '-{}'.format(self.release)
            # Set the download URL and return
            self.wf_download_url = 'https://github.com/{}/archive/{}.zip'.format(self.pipeline, self.release)
        else:
            logging.error("Not able to find pipeline '{}'".format(self.pipeline))
            logging.info("Available pipelines: {}".format(', '.join([w.name for w in wfs.remote_workflows])))
            raise LookupError("Not able to find pipeline '{}'".format(self.pipeline))

    def download_wf_files(self):
        """Downloads workflow files from Github to the :attr:`self.outdir`.
        """
        logging.debug("Downloading {}".format(self.wf_download_url))

        # Download GitHub zip file into memory and extract
        url = requests.get(self.wf_download_url)
        zipfile = ZipFile(BytesIO(url.content))
        zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        gh_name = '{}-{}'.format(self.wf_name, self.wf_sha).split('/')[-1]
        os.rename(os.path.join(self.outdir, gh_name), os.path.join(self.outdir, 'workflow'))

    def find_container_images(self):
        """ Find container image names for workflow """

        # Use linting code to parse the pipeline nextflow config
        self.config = nf_core.utils.fetch_wf_config(os.path.join(self.outdir, 'workflow'))

        # Find any config variables that look like a container
        for k,v in self.config.items():
            if k.startswith('process.') and k.endswith('.container'):
                self.containers.append(v.strip('"').strip("'"))


    def pull_singularity_image(self, container):
        """Uses a local installation of singularity to pull an image from Docker Hub.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to `nfcore/name:dev`.

        Raises:
            Various exceptions possible from `subprocess` execution of Singularity.
        """
        out_name = '{}.simg'.format(container.replace('nfcore', 'nf-core').replace('/','-').replace(':', '-'))
        out_path = os.path.abspath(os.path.join(self.outdir, 'singularity-images', out_name))
        address = 'docker://{}'.format(container.replace('docker://', ''))
        singularity_command = ["singularity", "pull", "--name", out_path, address]
        logging.info("Building singularity image from dockerhub: {}".format(address))
        logging.debug("Singularity command: {}".format(' '.join(singularity_command)))

        # Try to use singularity to pull image
        try:
            subprocess.call(singularity_command)
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                # Singularity is not installed
                logging.error('Singularity is not installed!')
            else:
                # Something else went wrong with singularity command
                raise e

    def validate_md5(self, fname, expected):
        """Calculates the md5sum for a file on the disk and validate with expected.

        Args:
            fname (str): Path to a local file.
            expected (str): The expected md5sum.

        Raises:
            IOError, if the md5sum does not match the remote sum.
        """
        logging.debug("Validating image hash: {}".format(fname))

        # Calculate the md5 for the file on disk
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()

        if file_hash == expected:
            logging.debug('md5 sum of image matches expected: {}'.format(expected))
        else:
            raise IOError ("{} md5 does not match remote: {} - {}".format(fname, expected, file_hash))
