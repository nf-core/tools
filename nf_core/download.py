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
import concurrent.futures
from rich.progress import BarColumn, DownloadColumn, TransferSpeedColumn, Progress
from zipfile import ZipFile

import nf_core
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
                    "[magenta]{task.description}",
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "•",
                    "[green]{task.completed}/{task.total} completed",
                )
            if task.fields.get("progress_type") == "download":
                self.columns = (
                    "[blue]{task.description}",
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn(),
                )
            if task.fields.get("progress_type") == "singularity_pull":
                self.columns = (
                    "[magenta]{task.description}",
                    "[blue]{task.fields[current_log]}",
                    BarColumn(bar_width=None),
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

    def __init__(
        self,
        pipeline,
        release=None,
        outdir=None,
        compress_type="tar.gz",
        force=False,
        singularity=False,
        singularity_cache_only=False,
        parallel_downloads=4,
    ):
        self.pipeline = pipeline
        self.release = release
        self.outdir = outdir
        self.output_filename = None
        self.compress_type = compress_type
        if self.compress_type == "none":
            self.compress_type = None
        self.force = force
        self.singularity = singularity
        self.singularity_cache_only = singularity_cache_only
        self.parallel_downloads = parallel_downloads

        # Sanity checks
        if self.singularity_cache_only and not self.singularity:
            log.error("Command has '--singularity-cache' set, but not '--singularity'")
            sys.exit(1)

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
        log.debug("Editing 'params.custom_config_base' in '{}'".format(nfconfig_fn))

        # Load the nextflow.config file into memory
        with open(nfconfig_fn, "r") as nfconfig_fh:
            nfconfig = nfconfig_fh.read()

        # Replace the target string
        nfconfig = nfconfig.replace(find_str, repl_str)

        # Append the singularity.cacheDir to the end if we need it
        if self.singularity and not self.singularity_cache_only:
            nfconfig += (
                f"\n\n// Added by `nf-core download` v{nf_core.__version__} //\n"
                + 'singularity.cacheDir = "${projectDir}/../singularity-images/"'
                + "\n///////////////////////////////////////"
            )

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

        log.info("Fetching container names for workflow")

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

        # Remove duplicates and sort
        self.containers = sorted(list(set(self.containers)))

        log.info("Found {} container{}".format(len(self.containers), "s" if len(self.containers) > 1 else ""))

    def get_singularity_images(self):
        """Loop through container names and download Singularity images"""

        if len(self.containers) == 0:
            log.info("No container names found in workflow")
        else:
            if not os.environ.get("NXF_SINGULARITY_CACHEDIR"):
                log.info(
                    "[magenta]Tip: Set env var $NXF_SINGULARITY_CACHEDIR to use a central cache for container downloads"
                )

            with DownloadProgress() as progress:
                task = progress.add_task("all_containers", total=len(self.containers), progress_type="summary")

                # Organise containers based on what we need to do with them
                containers_exist = []
                containers_cache = []
                containers_download = []
                containers_pull = []
                for container in self.containers:

                    # Fetch the output and cached filenames for this container
                    out_path, cache_path = self.singularity_image_filenames(container)

                    # Check that the directories exist
                    out_path_dir = os.path.dirname(out_path)
                    if not os.path.isdir(out_path_dir):
                        log.debug(f"Output directory not found, creating: {out_path_dir}")
                        os.makedirs(out_path_dir)
                    if cache_path:
                        cache_path_dir = os.path.dirname(cache_path)
                        if not os.path.isdir(cache_path_dir):
                            log.debug(f"Cache directory not found, creating: {cache_path_dir}")
                            os.makedirs(cache_path_dir)

                    # We already have the target file in place, return
                    if os.path.exists(out_path):
                        containers_exist.append(container)
                        continue

                    # We have a copy of this in the NXF_SINGULARITY_CACHE dir
                    if cache_path and os.path.exists(cache_path):
                        containers_cache.append([container, out_path, cache_path])
                        continue

                    # Direct download within Python
                    if container.startswith("http"):
                        containers_download.append([container, out_path, cache_path])
                        continue

                    # Pull using singularity
                    containers_pull.append([container, out_path, cache_path])

                # Go through each method of fetching containers in order
                for container in containers_exist:
                    progress.update(task, description="Image file exists")
                    progress.update(task, advance=1)

                for container in containers_cache:
                    progress.update(task, description=f"Copying singularity images from cache")
                    self.singularity_copy_cache_image(*container)
                    progress.update(task, advance=1)

                with concurrent.futures.ThreadPoolExecutor(max_workers=self.parallel_downloads) as pool:
                    progress.update(task, description="Downloading singularity images")

                    # Kick off concurrent downloads
                    future_downloads = [
                        pool.submit(self.singularity_download_image, *container, progress)
                        for container in containers_download
                    ]

                    # Make ctrl-c work with multi-threading
                    self.kill_with_fire = False

                    try:
                        # Iterate over each threaded download, waiting for them to finish
                        for future in concurrent.futures.as_completed(future_downloads):
                            try:
                                future.result()
                            except Exception:
                                raise
                            else:
                                try:
                                    progress.update(task, advance=1)
                                except Exception as e:
                                    log.error(f"Error updating progress bar: {e}")

                    except KeyboardInterrupt:
                        # Cancel the future threads that haven't started yet
                        for future in future_downloads:
                            future.cancel()
                        # Set the variable that the threaded function looks for
                        # Will trigger an exception from each thread
                        self.kill_with_fire = True
                        # Re-raise exception on the main thread
                        raise

                for container in containers_pull:
                    progress.update(task, description="Pulling singularity images")
                    try:
                        self.singularity_pull_image(*container, progress)
                    except RuntimeWarning as r:
                        # Raise exception if this is not possible
                        log.error("Not able to pull image. Service might be down or internet connection is dead.")
                        raise r
                    progress.update(task, advance=1)

    def singularity_image_filenames(self, container):
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
        cache_path = None
        if os.environ.get("NXF_SINGULARITY_CACHEDIR"):
            cache_path = os.path.join(os.environ["NXF_SINGULARITY_CACHEDIR"], out_name)
            # Use only the cache - set this as the main output path
            if self.singularity_cache_only:
                out_path = cache_path
                cache_path = None
        elif self.singularity_cache_only:
            raise FileNotFoundError("'--singularity-cache' specified but no '$NXF_SINGULARITY_CACHEDIR' set!")

        return (out_path, cache_path)

    def singularity_copy_cache_image(self, container, out_path, cache_path):
        """Copy Singularity image from NXF_SINGULARITY_CACHEDIR to target folder."""
        # Copy to destination folder if we have a cached version
        if cache_path and os.path.exists(cache_path):
            log.debug("Copying {} from cache: '{}'".format(container, os.path.basename(out_path)))
            shutil.copyfile(cache_path, out_path)

    def singularity_download_image(self, container, out_path, cache_path, progress):
        """Download a singularity image from the web.

        Use native Python to download the file.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``https://depot.galaxyproject.org/singularity/name:version``
            out_path (str): The final target output path
            cache_path (str, None): The NXF_SINGULARITY_CACHEDIR path if set, None if not
            progress (Progress): Rich progress bar instance to add tasks to.
        """
        log.debug(f"Downloading Singularity image: '{container}'")

        # Set output path to save file to
        output_path = cache_path or out_path
        output_path_tmp = f"{output_path}.partial"
        log.debug(f"Downloading to: '{output_path_tmp}'")

        # Set up progress bar
        nice_name = container.split("/")[-1][:50]
        task = progress.add_task(nice_name, start=False, total=False, progress_type="download")
        try:
            # Delete temporary file if it already exists
            if os.path.exists(output_path_tmp):
                os.remove(output_path_tmp)

            # Open file handle and download
            with open(output_path_tmp, "wb") as fh:
                # Disable caching as this breaks streamed downloads
                with requests_cache.disabled():
                    r = requests.get(container, allow_redirects=True, stream=True, timeout=60 * 5)
                    filesize = r.headers.get("Content-length")
                    if filesize:
                        progress.update(task, total=int(filesize))
                        progress.start_task(task)

                    # Stream download
                    for data in r.iter_content(chunk_size=4096):
                        # Check that the user didn't hit ctrl-c
                        if self.kill_with_fire:
                            raise KeyboardInterrupt
                        progress.update(task, advance=len(data))
                        fh.write(data)

            # Rename partial filename to final filename
            os.rename(output_path_tmp, output_path)
            output_path_tmp = None

            # Copy cached download if we are using the cache
            if cache_path:
                log.debug("Copying {} from cache: '{}'".format(container, os.path.basename(out_path)))
                progress.update(task, description="Copying from cache to target directory")
                shutil.copyfile(cache_path, out_path)

            progress.remove_task(task)

        except:
            # Kill the progress bars
            for t in progress.task_ids:
                progress.remove_task(t)
            # Try to delete the incomplete download
            log.debug(f"Deleting incompleted singularity image download:\n'{output_path_tmp}'")
            if output_path_tmp and os.path.exists(output_path_tmp):
                os.remove(output_path_tmp)
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
            # Re-raise the caught exception
            raise

    def singularity_pull_image(self, container, out_path, cache_path, progress):
        """Pull a singularity image using ``singularity pull``

        Attempt to use a local installation of singularity to pull the image.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``nfcore/name:version``.

        Raises:
            Various exceptions possible from `subprocess` execution of Singularity.
        """
        output_path = cache_path or out_path

        # Pull using singularity
        address = "docker://{}".format(container.replace("docker://", ""))
        singularity_command = ["singularity", "pull", "--name", output_path, address]
        log.debug("Building singularity image: {}".format(address))
        log.debug("Singularity command: {}".format(" ".join(singularity_command)))

        # Progress bar to show that something is happening
        task = progress.add_task(container, start=False, total=False, progress_type="singularity_pull", current_log="")

        # Try to use singularity to pull image
        try:
            # Run the singularity pull command
            proc = subprocess.Popen(
                singularity_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )
            for line in proc.stdout:
                log.debug(line.strip())
                progress.update(task, current_log=line.strip())

            # Copy cached download if we are using the cache
            if cache_path:
                log.debug("Copying {} from cache: '{}'".format(container, os.path.basename(out_path)))
                progress.update(task, current_log="Copying from cache to target directory")
                shutil.copyfile(cache_path, out_path)

            progress.remove_task(task)

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
