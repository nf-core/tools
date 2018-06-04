#!/usr/bin/env python
""" Download a nf-core pipeline """

from __future__ import print_function

from io import BytesIO
import logging
import os
import re
import requests
import subprocess
import sys
from zipfile import ZipFile


import nf_core.list, nf_core.utils

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
        self.config = dict()
        self.containers = list()

    def download_workflow(self):
        """ Main function to download a nf-core workflow """

        # Get workflow details
        try:
            self.fetch_workflow_details()
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
            logging.info("Fetching container names for workflow")
            self.find_singularity_images()
            if len(self.containers) == 0:
                logging.info("No container names found in workflow")
            else:
                os.mkdir(os.path.join(self.outdir, 'singularity-images'))
                for container in self.containers:
                    self.download_singularity_image(container)


    def fetch_workflow_details(self):
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
                    logging.info("Pipeline is in development. Using current code on master branch.")

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
        """ Download workflow files from GitHub - save in outdir """
        logging.debug("Downloading {}".format(self.wf_download_url))

        # Download GitHub zip file into memory and extract
        url = requests.get(self.wf_download_url)
        zipfile = ZipFile(BytesIO(url.content))
        zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        gh_name = '{}-{}'.format(self.wf_name, self.wf_sha).split('/')[-1]
        os.rename(os.path.join(self.outdir, gh_name), os.path.join(self.outdir, 'workflow'))

    def find_singularity_images(self):
        """ Find singularity image names for workflow """

        # Use linting code to parse the pipeline nextflow config
        self.config = nf_core.utils.fetch_wf_config(os.path.join(self.outdir, 'workflow'))

        # Find any config variables that look like a container
        for k,v in self.config.items():
            if k.startswith('process.') and k.endswith('.container'):
                self.containers.append(v.strip('"').strip("'"))

    def download_singularity_image(self, container):
        """ Download singularity images for workflow """

        out_name = '{}.simg'.format(container.replace('nfcore', 'nf-core').replace('/','-').replace(':', '-'))
        out_path = os.path.abspath(os.path.join(self.outdir, 'singularity-images', out_name))
        address = 'docker://{}'.format(container.replace('docker://', ''))
        shub_api_url = 'https://www.singularity-hub.org/api/container/{}'.format(container.replace('nfcore', 'nf-core').replace('docker://', ''))
        shub_api_url = 'https://www.singularity-hub.org/api/container/ewels/nf-core-methylseq:latest'
        singularity_command = ["singularity", "pull", "--name", out_path, address]

        # Try to download the singularity image from singularity-hub first
        logging.debug("Checking shub API: {}".format(shub_api_url))
        response = requests.get(shub_api_url, timeout=10)
        if response.status_code == 200:
            shub_response = response.json()
            logging.info("Downloading singularity image from singularity-hub.org")

            # Strip the ?generation= key in URL, as this breaks the download

            #
            # TODO: May not need to do this?
            #
            dl_url = re.sub(r"\?generation=\d+&", '?', shub_response['image'])

            # Stream the download as it's going to be large
            logging.debug("Starting download: {}".format(dl_url))

            #
            # TODO: This next line hangs! WHHYYYYYY?Y???????
            #
            dl_request = requests.get(dl_url, stream=True)
            if dl_request.status_code == 200:
                logging.debug("Response code 200. Streaming download to disk.")
                with open(out_path, 'wb') as f:
                    for chunk in dl_request.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                return
            else:
                logging.error("Error with singularity hub API call: {}".format(response.status_code))

#             dl_request = requests.get(shub_response['image'], stream=True)
#             total_length = int(dl_request.headers.get('content-length'))
#             logging.debug("Total image file size: {} bytes".format(total_length))
#             with click.progressbar(dl_request.iter_content(1024), length=total_size) as pbar, open(out_path, 'wb') as f:
#                 for chunk in pbar:
#                     if chunk:
#                         f.write(chunk)
#                         pbar.update(len(chunk))

        logging.debug("Singularity image not found on singularity-hub")
        logging.info("Building singularity image '{}'".format(out_name))
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
