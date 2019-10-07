#!/usr/bin/env python
"""Downloads a nf-core pipeline to the local file system."""

from __future__ import print_function

import errno
from io import BytesIO
import logging
import hashlib
import os
import requests
import shutil
import subprocess
import sys
import tarfile
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
    def __init__(self, pipeline, release=None, singularity=False, outdir=None, compress_type='tar.gz'):
        self.pipeline = pipeline
        self.release = release
        self.singularity = singularity
        self.outdir = outdir
        self.output_filename = None
        self.compress_type = compress_type
        if self.compress_type == 'none':
            self.compress_type = None

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

        output_logmsg = "Output directory: {}".format(self.outdir)

        # Set an output filename now that we have the outdir
        if self.compress_type is not None:
            self.output_filename = '{}.{}'.format(self.outdir, self.compress_type)
            output_logmsg = "Output file: {}".format(self.output_filename)

        # Check that the outdir doesn't already exist
        if os.path.exists(self.outdir):
            logging.error("Output directory '{}' already exists".format(self.outdir))
            sys.exit(1)

        # Check that compressed output file doesn't already exist
        if self.output_filename and os.path.exists(self.output_filename):
            logging.error("Output file '{}' already exists".format(self.output_filename))
            sys.exit(1)

        logging.info(
            "Saving {}".format(self.pipeline) +
            "\n Pipeline release: {}".format(self.release) +
            "\n Pull singularity containers: {}".format('Yes' if self.singularity else 'No') +
            "\n {}".format(output_logmsg)
        )

        # Download the pipeline files
        logging.info("Downloading workflow files from GitHub")
        self.download_wf_files()

        # Download the centralised configs
        logging.info("Downloading centralised configs from GitHub")
        self.download_configs()
        self.wf_use_local_configs()

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

        # Compress into an archive
        if self.compress_type is not None:
            logging.info("Compressing download..")
            self.compress_download()


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
                    # Sort list of releases so that most recent is first
                    wf.releases = sorted(wf.releases, key=lambda k: k.get('published_at_timestamp', 0), reverse=True)
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
                    logging.warning("Pipeline is in development - downloading current code on master branch.\n" +
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
            logging.warning("Pipeline name doesn't match any nf-core workflows")
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

        # Make downloaded files executable
        for dirpath, subdirs, filelist in os.walk(os.path.join(self.outdir, 'workflow')):
            for fname in filelist:
                os.chmod(os.path.join(dirpath, fname), 0o775)

    def download_configs(self):
        """Downloads the centralised config profiles from nf-core/configs to :attr:`self.outdir`.
        """
        configs_zip_url = "https://github.com/nf-core/configs/archive/master.zip"
        configs_local_dir = "configs-master"
        logging.debug("Downloading {}".format(configs_zip_url))

        # Download GitHub zip file into memory and extract
        url = requests.get(configs_zip_url)
        zipfile = ZipFile(BytesIO(url.content))
        zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        os.rename(os.path.join(self.outdir, configs_local_dir), os.path.join(self.outdir, 'configs'))

        # Make downloaded files executable
        for dirpath, subdirs, filelist in os.walk(os.path.join(self.outdir, 'configs')):
            for fname in filelist:
                os.chmod(os.path.join(dirpath, fname), 0o775)

    def wf_use_local_configs(self):
        """Edit the downloaded nextflow.config file to use the local config files
        """
        nfconfig_fn = os.path.join(self.outdir, 'workflow', 'nextflow.config')
        find_str = 'https://raw.githubusercontent.com/nf-core/configs/${params.custom_config_version}'
        repl_str = '../configs/'
        logging.debug("Editing params.custom_config_base in {}".format(nfconfig_fn))

        # Load the nextflow.config file into memory
        with open(nfconfig_fn, 'r') as nfconfig_fh:
          nfconfig = nfconfig_fh.read()

        # Replace the target string
        nfconfig = nfconfig.replace(find_str, repl_str)

        # Write the file out again
        with open(nfconfig_fn, 'w') as nfconfig_fh:
          nfconfig_fh.write(nfconfig)


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
            if e.errno == errno.ENOENT:
                # Singularity is not installed
                logging.error('Singularity is not installed!')
            else:
                # Something else went wrong with singularity command
                raise e

    def compress_download(self):
        """Take the downloaded files and make a compressed .tar.gz archive.
        """
        logging.debug('Creating archive: {}'.format(self.output_filename))

        # .tar.gz and .tar.bz2 files
        if self.compress_type == 'tar.gz' or self.compress_type == 'tar.bz2':
            ctype = self.compress_type.split('.')[1]
            with tarfile.open(self.output_filename, "w:{}".format(ctype)) as tar:
                tar.add(self.outdir, arcname=os.path.basename(self.outdir))
            tar_flags = 'xzf' if ctype == 'gz' else 'xjf'
            logging.info('Command to extract files: tar -{} {}'.format(tar_flags, self.output_filename))

        # .zip files
        if self.compress_type == 'zip':
            with ZipFile(self.output_filename, 'w') as zipObj:
               # Iterate over all the files in directory
               for folderName, subfolders, filenames in os.walk(self.outdir):
                   for filename in filenames:
                       #create complete filepath of file in directory
                       filePath = os.path.join(folderName, filename)
                       # Add file to zip
                       zipObj.write(filePath)
            logging.info('Command to extract files: unzip {}'.format(self.output_filename))

        # Delete original files
        logging.debug('Deleting uncompressed files: {}'.format(self.outdir))
        shutil.rmtree(self.outdir)

        # Caclualte md5sum for output file
        self.validate_md5(self.output_filename)


    def validate_md5(self, fname, expected=None):
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

        if expected is None:
            logging.info("MD5 checksum for {}: {}".format(fname, file_hash))
        else:
            if file_hash == expected:
                logging.debug('md5 sum of image matches expected: {}'.format(expected))
            else:
                raise IOError ("{} md5 does not match remote: {} - {}".format(fname, expected, file_hash))
