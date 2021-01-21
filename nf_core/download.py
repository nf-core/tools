#!/usr/bin/env python
"""Downloads a nf-core pipeline to the local file system."""

from __future__ import print_function

import errno
from io import BytesIO
import logging
import hashlib
import os
import re
import requests
import requests_cache
import shutil
import subprocess
import sys
import tarfile
from rich.progress import BarColumn, DownloadColumn, TextColumn, TransferSpeedColumn, Progress
from zipfile import ZipFile

import nf_core.list
import nf_core.utils

log = logging.getLogger(__name__)


class DownloadProgress(Progress):
    """Custom Progress bar class, allowing us to have two progress
    bars with different columns / layouts.
    """

    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "summary":
                self.columns = (
                    TextColumn(
                        "[magenta]Downloading [bold green]{}[/bold green] singularity container{}".format(
                            task.total, "s" if task.total > 1 else ""
                        ),
                        justify="right",
                    ),
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "•",
                    TextColumn("[green]{task.completed}/{task.total} completed", justify="right"),
                )
            if task.fields.get("progress_type") == "download":
                self.columns = (
                    TextColumn("[blue]{task.fields[container]}", justify="right"),
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn(),
                )
            yield self.make_tasks_table([task])


class DownloadWorkflow(object):
    """Downloads a nf-core workflow from GitHub to the local file system.

    Can also download its Singularity container image if required.

    Args:
        pipeline (str): A nf-core pipeline name.
        release (str): The workflow release version to download, like `1.0`. Defaults to None.
        singularity (bool): Flag, if the Singularity container should be downloaded as well. Defaults to False.
        outdir (str): Path to the local download directory. Defaults to None.
    """

    def __init__(self, pipeline, release=None, singularity=False, outdir=None, compress_type="tar.gz", force=False):
        self.pipeline = pipeline
        self.release = release
        self.singularity = singularity
        self.outdir = outdir
        self.output_filename = None
        self.compress_type = compress_type
        if self.compress_type == "none":
            self.compress_type = None
        self.force = force

        self.wf_name = None
        self.wf_sha = None
        self.wf_download_url = None
        self.nf_config = dict()
        self.containers = list()

    def download_workflow(self):
        """Starts a nf-core workflow download."""
        # Get workflow details
        try:
            self.fetch_workflow_details(nf_core.list.Workflows())
        except LookupError:
            sys.exit(1)

        summary_log = [
            "Pipeline release: '{}'".format(self.release),
            "Pull singularity containers: '{}'".format("Yes" if self.singularity else "No"),
        ]
        if self.singularity and os.environ.get("NXF_SINGULARITY_CACHEDIR"):
            summary_log.append("Using '$NXF_SINGULARITY_CACHEDIR': {}".format(os.environ["NXF_SINGULARITY_CACHEDIR"]))

        # Set an output filename now that we have the outdir
        if self.compress_type is not None:
            self.output_filename = f"{self.outdir}.{self.compress_type}"
            summary_log.append(f"Output file: '{self.output_filename}'")
        else:
            summary_log.append(f"Output directory: '{self.outdir}'")

        # Check that the outdir doesn't already exist
        if os.path.exists(self.outdir):
            if not self.force:
                log.error(f"Output directory '{self.outdir}' already exists (use [red]--force[/] to overwrite)")
                sys.exit(1)
            log.warning(f"Deleting existing output directory: '{self.outdir}'")
            shutil.rmtree(self.outdir)

        # Check that compressed output file doesn't already exist
        if self.output_filename and os.path.exists(self.output_filename):
            if not self.force:
                log.error(f"Output file '{self.output_filename}' already exists (use [red]--force[/] to overwrite)")
                sys.exit(1)
            log.warning(f"Deleting existing output file: '{self.output_filename}'")
            os.remove(self.output_filename)

        # Summary log
        log.info("Saving {}\n {}".format(self.pipeline, "\n ".join(summary_log)))

        # Download the pipeline files
        log.info("Downloading workflow files from GitHub")
        self.download_wf_files()

        # Download the centralised configs
        log.info("Downloading centralised configs from GitHub")
        self.download_configs()
        self.wf_use_local_configs()

        # Download the singularity images
        if self.singularity:
            log.debug("Fetching container names for workflow")
            self.find_container_images()
            self.get_singularity_images()

        # Compress into an archive
        if self.compress_type is not None:
            log.info("Compressing download..")
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
                    wf.releases = sorted(wf.releases, key=lambda k: k.get("published_at_timestamp", 0), reverse=True)
                    self.release = wf.releases[0]["tag_name"]
                    self.wf_sha = wf.releases[0]["tag_sha"]
                    log.debug("No release specified. Using latest release: {}".format(self.release))
                # Find specified release hash
                elif self.release is not None:
                    for r in wf.releases:
                        if r["tag_name"] == self.release.lstrip("v"):
                            self.wf_sha = r["tag_sha"]
                            break
                    else:
                        log.error("Not able to find release '{}' for {}".format(self.release, wf.full_name))
                        log.info(
                            "Available {} releases: {}".format(
                                wf.full_name, ", ".join([r["tag_name"] for r in wf.releases])
                            )
                        )
                        raise LookupError("Not able to find release '{}' for {}".format(self.release, wf.full_name))

                # Must be a dev-only pipeline
                elif not self.release:
                    self.release = "dev"
                    self.wf_sha = "master"  # Cheating a little, but GitHub download link works
                    log.warning(
                        "Pipeline is in development - downloading current code on master branch.\n"
                        + "This is likely to change soon should not be considered fully reproducible."
                    )

                # Set outdir name if not defined
                if not self.outdir:
                    self.outdir = "nf-core-{}".format(wf.name)
                    if self.release is not None:
                        self.outdir += "-{}".format(self.release)

                # Set the download URL and return
                self.wf_download_url = "https://github.com/{}/archive/{}.zip".format(wf.full_name, self.wf_sha)
                return

        # If we got this far, must not be a nf-core pipeline
        if self.pipeline.count("/") == 1:
            # Looks like a GitHub address - try working with this repo
            log.warning("Pipeline name doesn't match any nf-core workflows")
            log.info("Pipeline name looks like a GitHub address - attempting to download anyway")
            self.wf_name = self.pipeline
            if not self.release:
                self.release = "master"
            self.wf_sha = self.release
            if not self.outdir:
                self.outdir = self.pipeline.replace("/", "-").lower()
                if self.release is not None:
                    self.outdir += "-{}".format(self.release)
            # Set the download URL and return
            self.wf_download_url = "https://github.com/{}/archive/{}.zip".format(self.pipeline, self.release)
        else:
            log.error("Not able to find pipeline '{}'".format(self.pipeline))
            log.info("Available pipelines: {}".format(", ".join([w.name for w in wfs.remote_workflows])))
            raise LookupError("Not able to find pipeline '{}'".format(self.pipeline))

    def download_wf_files(self):
        """Downloads workflow files from GitHub to the :attr:`self.outdir`."""
        log.debug("Downloading {}".format(self.wf_download_url))

        # Download GitHub zip file into memory and extract
        url = requests.get(self.wf_download_url)
        zipfile = ZipFile(BytesIO(url.content))
        zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        gh_name = "{}-{}".format(self.wf_name, self.wf_sha).split("/")[-1]
        os.rename(os.path.join(self.outdir, gh_name), os.path.join(self.outdir, "workflow"))

        # Make downloaded files executable
        for dirpath, subdirs, filelist in os.walk(os.path.join(self.outdir, "workflow")):
            for fname in filelist:
                os.chmod(os.path.join(dirpath, fname), 0o775)

    def download_configs(self):
        """Downloads the centralised config profiles from nf-core/configs to :attr:`self.outdir`."""
        configs_zip_url = "https://github.com/nf-core/configs/archive/master.zip"
        configs_local_dir = "configs-master"
        log.debug("Downloading {}".format(configs_zip_url))

        # Download GitHub zip file into memory and extract
        url = requests.get(configs_zip_url)
        zipfile = ZipFile(BytesIO(url.content))
        zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        os.rename(os.path.join(self.outdir, configs_local_dir), os.path.join(self.outdir, "configs"))

        # Make downloaded files executable
        for dirpath, subdirs, filelist in os.walk(os.path.join(self.outdir, "configs")):
            for fname in filelist:
                os.chmod(os.path.join(dirpath, fname), 0o775)

    def wf_use_local_configs(self):
        """Edit the downloaded nextflow.config file to use the local config files"""
        nfconfig_fn = os.path.join(self.outdir, "workflow", "nextflow.config")
        find_str = "https://raw.githubusercontent.com/nf-core/configs/${params.custom_config_version}"
        repl_str = "../configs/"
        log.debug("Editing params.custom_config_base in {}".format(nfconfig_fn))

        # Load the nextflow.config file into memory
        with open(nfconfig_fn, "r") as nfconfig_fh:
            nfconfig = nfconfig_fh.read()

        # Replace the target string
        nfconfig = nfconfig.replace(find_str, repl_str)

        # Write the file out again
        with open(nfconfig_fn, "w") as nfconfig_fh:
            nfconfig_fh.write(nfconfig)

    def find_container_images(self):
        """Find container image names for workflow.

        Starts by using `nextflow config` to pull out any process.container
        declarations. This works for DSL1.

        Second, we look for DSL2 containers. These can't be found with
        `nextflow config` at the time of writing, so we scrape the pipeline files.
        """

        # Use linting code to parse the pipeline nextflow config
        self.nf_config = nf_core.utils.fetch_wf_config(os.path.join(self.outdir, "workflow"))

        # Find any config variables that look like a container
        for k, v in self.nf_config.items():
            if k.startswith("process.") and k.endswith(".container"):
                self.containers.append(v.strip('"').strip("'"))

        # Recursive search through any DSL2 module files for container spec lines.
        for subdir, dirs, files in os.walk(os.path.join(self.outdir, "workflow", "modules")):
            for file in files:
                if file.endswith(".nf"):
                    with open(os.path.join(subdir, file), "r") as fh:
                        # Look for any lines with `container = "xxx"`
                        matches = []
                        for line in fh:
                            match = re.match(r"\s*container\s+[\"']([^\"']+)[\"']", line)
                            if match:
                                matches.append(match.group(1))

                        # If we have matches, save the first one that starts with http
                        for m in matches:
                            if m.startswith("http"):
                                self.containers.append(m.strip('"').strip("'"))
                                break
                        # If we get here then we didn't call break - just save the first match
                        else:
                            if len(matches) > 0:
                                self.containers.append(matches[0].strip('"').strip("'"))

    def get_singularity_images(self):
        """Loop through container names and download Singularity images"""
        # Remove duplicates and sort
        # (running in the same order each time is less frustrating with caching etc)
        self.containers = sorted(list(set(self.containers)))

        if len(self.containers) == 0:
            log.info("No container names found in workflow")
        else:
            os.mkdir(os.path.join(self.outdir, "singularity-images"))
            if not os.environ.get("NXF_SINGULARITY_CACHEDIR"):
                log.info(
                    "[magenta]Tip: Set env var $NXF_SINGULARITY_CACHEDIR to use a central cache for container downloads"
                )

            with DownloadProgress() as progress:
                task = progress.add_task("all_containers", total=len(self.containers), progress_type="summary")
                for container in self.containers:
                    progress.update(task, advance=1)
                    try:
                        # Copy from the cache if we can, generate download path if not
                        output_path = self.singularity_copy_cache_image(container)
                        # Copied from cache
                        if output_path is True:
                            continue

                        # Direct download within Python
                        if container.startswith("http"):
                            self.singularity_download_image(container, output_path, progress)

                        # Pull using singularity
                        else:
                            self.singularity_pull_image(container, output_path)

                        # Run cache copy again in case we pulled to the cache
                        self.singularity_copy_cache_image(container)

                    except RuntimeWarning as r:
                        # Raise exception if this is not possible
                        log.error("Not able to pull image. Service might be down or internet connection is dead.")
                        raise r

    def singularity_copy_cache_image(self, container):
        """Check Singularity cache for image, copy to destination folder if found.

        Args:
            container (str): A pipeline's container name. Can be direct download URL
                             or a Docker Hub repository ID.

        Returns:
            results (bool, str): Returns True if we have the image in the target location.
                                 Returns a download path if not.
        """

        # Generate file paths
        # Based on simpleName() function in Nextflow code:
        # https://github.com/nextflow-io/nextflow/blob/671ae6d85df44f906747c16f6d73208dbc402d49/modules/nextflow/src/main/groovy/nextflow/container/SingularityCache.groovy#L69-L94
        out_name = container
        # Strip URI prefix
        out_name = re.sub(r"^.*:\/\/", "", out_name)
        # Detect file extension
        extension = ".img"
        if ".sif:" in out_name:
            extension = ".sif"
            out_name = out_name.replace(".sif:", "-")
        elif out_name.endswith(".sif"):
            extension = ".sif"
            out_name = out_name[:-4]
        # Strip : and / characters
        out_name = out_name.replace("/", "-").replace(":", "-")
        # Stupid Docker Hub not allowing hyphens
        out_name = out_name.replace("nfcore", "nf-core")
        # Add file extension
        out_name = out_name + extension

        # Full destination and cache paths
        out_path = os.path.abspath(os.path.join(self.outdir, "singularity-images", out_name))
        dl_path = out_path
        if os.environ.get("NXF_SINGULARITY_CACHEDIR"):
            dl_path = os.path.join(os.environ["NXF_SINGULARITY_CACHEDIR"], out_name)

        # We already have the target file in place, return
        # Typical for second run of this function after pulling if no cachedir in place
        if os.path.exists(out_path):
            return True

        # Copy to destination folder if we have a cached version
        if os.path.exists(dl_path):
            log.debug(f"Copying Singularity image from cache: '{out_name}'")
            shutil.copyfile(dl_path, out_path)
            return True

        # No cached version found, return download path
        return dl_path

    def singularity_download_image(self, container, output_path, progress):
        """Download a singularity image from the web.

        Use native Python to download the file.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``https://depot.galaxyproject.org/singularity/name:version``
        """
        # Set up progress bar
        nice_name = container.split("/")[-1][:50]
        task = progress.add_task("download", container=nice_name, start=False, total=False, progress_type="download")
        try:
            with open(output_path, "wb") as fh:
                # Disable caching as this breaks streamed downloads
                with requests_cache.disabled():
                    r = requests.get(container, allow_redirects=True, stream=True, timeout=60 * 5)
                    filesize = r.headers.get("Content-length")
                    if filesize:
                        progress.update(task, total=int(filesize))
                        progress.start_task(task)

                    # Stream download
                    for data in r.iter_content(chunk_size=4096):
                        progress.update(task, advance=len(data))
                        fh.write(data)

                progress.remove_task(task)

        except:
            # Kill the progress bars
            for t in progress.task_ids:
                progress.remove_task(t)
            # Try to delete the incomplete download
            log.warning(f"Deleting incompleted download: '{output_path}'")
            os.remove(output_path)
            # Re-raise the caught exception
            raise

    def singularity_pull_image(self, container, output_path):
        """Pull a singularity image using ``singularity pull``

        Attempt to use a local installation of singularity to pull the image.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``nfcore/name:version``.

        Raises:
            Various exceptions possible from `subprocess` execution of Singularity.
        """
        # Pull using singularity
        address = "docker://{}".format(container.replace("docker://", ""))
        singularity_command = ["singularity", "pull", "--name", output_path, address]
        log.info("Building singularity image: {}".format(address))
        log.debug("Singularity command: {}".format(" ".join(singularity_command)))

        # Try to use singularity to pull image
        try:
            subprocess.call(singularity_command)
        except OSError as e:
            if e.errno == errno.ENOENT:
                # Singularity is not installed
                log.error("Singularity is not installed!")
            else:
                # Something else went wrong with singularity command
                raise e

    def compress_download(self):
        """Take the downloaded files and make a compressed .tar.gz archive."""
        log.debug("Creating archive: {}".format(self.output_filename))

        # .tar.gz and .tar.bz2 files
        if self.compress_type == "tar.gz" or self.compress_type == "tar.bz2":
            ctype = self.compress_type.split(".")[1]
            with tarfile.open(self.output_filename, "w:{}".format(ctype)) as tar:
                tar.add(self.outdir, arcname=os.path.basename(self.outdir))
            tar_flags = "xzf" if ctype == "gz" else "xjf"
            log.info("Command to extract files: tar -{} {}".format(tar_flags, self.output_filename))

        # .zip files
        if self.compress_type == "zip":
            with ZipFile(self.output_filename, "w") as zipObj:
                # Iterate over all the files in directory
                for folderName, subfolders, filenames in os.walk(self.outdir):
                    for filename in filenames:
                        # create complete filepath of file in directory
                        filePath = os.path.join(folderName, filename)
                        # Add file to zip
                        zipObj.write(filePath)
            log.info("Command to extract files: unzip {}".format(self.output_filename))

        # Delete original files
        log.debug("Deleting uncompressed files: {}".format(self.outdir))
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
        log.debug("Validating image hash: {}".format(fname))

        # Calculate the md5 for the file on disk
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        file_hash = hash_md5.hexdigest()

        if expected is None:
            log.info("MD5 checksum for {}: {}".format(fname, file_hash))
        else:
            if file_hash == expected:
                log.debug("md5 sum of image matches expected: {}".format(expected))
            else:
                raise IOError("{} md5 does not match remote: {} - {}".format(fname, expected, file_hash))
