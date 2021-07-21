#!/usr/bin/env python
"""Downloads a nf-core pipeline to the local file system."""

from __future__ import print_function

from io import BytesIO
import logging
import hashlib
import os
import questionary
import re
import requests
import requests_cache
import shutil
import subprocess
import sys
import tarfile
import concurrent.futures
import rich
import rich.progress
from zipfile import ZipFile

import nf_core
import nf_core.list
import nf_core.utils

log = logging.getLogger(__name__)
stderr = rich.console.Console(
    stderr=True, style="dim", highlight=False, force_terminal=nf_core.utils.rich_force_colors()
)


class DownloadProgress(rich.progress.Progress):
    """Custom Progress bar class, allowing us to have two progress
    bars with different columns / layouts.
    """

    def get_renderables(self):
        for task in self.tasks:
            if task.fields.get("progress_type") == "summary":
                self.columns = (
                    "[magenta]{task.description}",
                    rich.progress.BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.0f}%",
                    "•",
                    "[green]{task.completed}/{task.total} completed",
                )
            if task.fields.get("progress_type") == "download":
                self.columns = (
                    "[blue]{task.description}",
                    rich.progress.BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    rich.progress.DownloadColumn(),
                    "•",
                    rich.progress.TransferSpeedColumn(),
                )
            if task.fields.get("progress_type") == "singularity_pull":
                self.columns = (
                    "[magenta]{task.description}",
                    "[blue]{task.fields[current_log]}",
                    rich.progress.BarColumn(bar_width=None),
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
        pipeline=None,
        release=None,
        outdir=None,
        compress_type=None,
        force=False,
        container=None,
        singularity_cache_only=False,
        parallel_downloads=4,
    ):
        self.pipeline = pipeline
        self.release = release
        self.outdir = outdir
        self.output_filename = None
        self.compress_type = compress_type
        self.force = force
        self.container = container
        self.singularity_cache_only = singularity_cache_only
        self.parallel_downloads = parallel_downloads

        self.wf_releases = {}
        self.wf_branches = {}
        self.wf_sha = None
        self.wf_download_url = None
        self.nf_config = dict()
        self.containers = list()

        # Fetch remote workflows
        self.wfs = nf_core.list.Workflows()
        self.wfs.get_remote_workflows()

    def download_workflow(self):
        """Starts a nf-core workflow download."""

        # Get workflow details
        try:
            self.prompt_pipeline_name()
            self.pipeline, self.wf_releases, self.wf_branches = nf_core.utils.get_repo_releases_branches(
                self.pipeline, self.wfs
            )
            self.prompt_release()
            self.get_release_hash()
            self.prompt_container_download()
            self.prompt_use_singularity_cachedir()
            self.prompt_singularity_cachedir_only()
            self.prompt_compression_type()
        except AssertionError as e:
            log.critical(e)
            sys.exit(1)

        summary_log = [f"Pipeline release: '{self.release}'", f"Pull containers: '{self.container}'"]
        if self.container == "singularity" and os.environ.get("NXF_SINGULARITY_CACHEDIR") is not None:
            summary_log.append(
                "Using [blue]$NXF_SINGULARITY_CACHEDIR[/]': {}".format(os.environ["NXF_SINGULARITY_CACHEDIR"])
            )

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
        log.info("Saving '{}'\n {}".format(self.pipeline, "\n ".join(summary_log)))

        # Download the pipeline files
        log.info("Downloading workflow files from GitHub")
        self.download_wf_files()

        # Download the centralised configs
        log.info("Downloading centralised configs from GitHub")
        self.download_configs()
        try:
            self.wf_use_local_configs()
        except FileNotFoundError as e:
            log.error("Error editing pipeline config file to use local configs!")
            log.critical(e)
            sys.exit(1)

        # Download the singularity images
        if self.container == "singularity":
            self.find_container_images()
            try:
                self.get_singularity_images()
            except OSError as e:
                log.critical(f"[red]{e}[/]")
                sys.exit(1)

        # Compress into an archive
        if self.compress_type is not None:
            log.info("Compressing download..")
            self.compress_download()

    def prompt_pipeline_name(self):
        """Prompt for the pipeline name if not set with a flag"""

        if self.pipeline is None:
            stderr.print("Specify the name of a nf-core pipeline or a GitHub repository name (user/repo).")
            self.pipeline = nf_core.utils.prompt_remote_pipeline_name(self.wfs)

    def prompt_release(self):
        """Prompt for pipeline release / branch"""
        # Prompt user for release tag if '--release' was not set
        if self.release is None:
            self.release = nf_core.utils.prompt_pipeline_release_branch(self.wf_releases, self.wf_branches)

    def get_release_hash(self):
        """Find specified release / branch hash"""

        # Branch
        if self.release in self.wf_branches.keys():
            self.wf_sha = self.wf_branches[self.release]

        # Release
        else:
            for r in self.wf_releases:
                if r["tag_name"] == self.release:
                    self.wf_sha = r["tag_sha"]
                    break

            # Can't find the release or branch - throw an error
            else:
                log.info(
                    "Available {} releases: '{}'".format(
                        self.pipeline, "', '".join([r["tag_name"] for r in self.wf_releases])
                    )
                )
                log.info("Available {} branches: '{}'".format(self.pipeline, "', '".join(self.wf_branches.keys())))
                raise AssertionError(
                    "Not able to find release / branch '{}' for {}".format(self.release, self.pipeline)
                )

        # Set the outdir
        if not self.outdir:
            self.outdir = "{}-{}".format(self.pipeline.replace("/", "-").lower(), self.release)

        # Set the download URL and return
        self.wf_download_url = "https://github.com/{}/archive/{}.zip".format(self.pipeline, self.wf_sha)

    def prompt_container_download(self):
        """Prompt whether to download container images or not"""

        if self.container is None:
            stderr.print("\nIn addition to the pipeline code, this tool can download software containers.")
            self.container = questionary.select(
                "Download software container images:",
                choices=["none", "singularity"],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

    def prompt_use_singularity_cachedir(self):
        """Prompt about using $NXF_SINGULARITY_CACHEDIR if not already set"""
        if (
            self.container == "singularity"
            and os.environ.get("NXF_SINGULARITY_CACHEDIR") is None
            and stderr.is_interactive  # Use rich auto-detection of interactive shells
        ):
            stderr.print(
                "\nNextflow and nf-core can use an environment variable called [blue]$NXF_SINGULARITY_CACHEDIR[/] that is a path to a directory where remote Singularity images are stored. "
                "This allows downloaded images to be cached in a central location."
            )
            if rich.prompt.Confirm.ask(
                f"[blue bold]?[/] [bold]Define [blue not bold]$NXF_SINGULARITY_CACHEDIR[/] for a shared Singularity image download folder?[/]"
            ):
                # Prompt user for a cache directory path
                cachedir_path = None
                while cachedir_path is None:
                    prompt_cachedir_path = questionary.path(
                        "Specify the path:", only_directories=True, style=nf_core.utils.nfcore_question_style
                    ).unsafe_ask()
                    cachedir_path = os.path.abspath(os.path.expanduser(prompt_cachedir_path))
                    if prompt_cachedir_path == "":
                        log.error(f"Not using [blue]$NXF_SINGULARITY_CACHEDIR[/]")
                        cachedir_path = False
                    elif not os.path.isdir(cachedir_path):
                        log.error(f"'{cachedir_path}' is not a directory.")
                        cachedir_path = None
                if cachedir_path:
                    os.environ["NXF_SINGULARITY_CACHEDIR"] = cachedir_path

                    # Ask if user wants this set in their .bashrc
                    bashrc_path = os.path.expanduser("~/.bashrc")
                    if not os.path.isfile(bashrc_path):
                        bashrc_path = os.path.expanduser("~/.bash_profile")
                        if not os.path.isfile(bashrc_path):
                            bashrc_path = False
                    if bashrc_path:
                        stderr.print(
                            f"\nSo that [blue]$NXF_SINGULARITY_CACHEDIR[/] is always defined, you can add it to your [blue not bold]~/{os.path.basename(bashrc_path)}[/] file ."
                            "This will then be autmoatically set every time you open a new terminal. We can add the following line to this file for you: \n"
                            f'[blue]export NXF_SINGULARITY_CACHEDIR="{cachedir_path}"[/]'
                        )
                        append_to_file = rich.prompt.Confirm.ask(
                            f"[blue bold]?[/] [bold]Add to [blue not bold]~/{os.path.basename(bashrc_path)}[/] ?[/]"
                        )
                        if append_to_file:
                            with open(os.path.expanduser(bashrc_path), "a") as f:
                                f.write(
                                    "\n\n#######################################\n"
                                    f"## Added by `nf-core download` v{nf_core.__version__} ##\n"
                                    + f'export NXF_SINGULARITY_CACHEDIR="{cachedir_path}"'
                                    + "\n#######################################\n"
                                )
                            log.info(f"Successfully wrote to [blue]{bashrc_path}[/]")
                            log.warning(
                                "You will need reload your terminal after the download completes for this to take effect."
                            )

    def prompt_singularity_cachedir_only(self):
        """Ask if we should *only* use $NXF_SINGULARITY_CACHEDIR without copying into target"""
        if (
            self.singularity_cache_only is None
            and self.container == "singularity"
            and os.environ.get("NXF_SINGULARITY_CACHEDIR") is not None
        ):
            stderr.print(
                "\nIf you are working on the same system where you will run Nextflow, you can leave the downloaded images in the "
                "[blue not bold]$NXF_SINGULARITY_CACHEDIR[/] folder, Nextflow will automatically find them. "
                "However if you will transfer the downloaded files to a different system then they should be copied to the target folder."
            )
            self.singularity_cache_only = rich.prompt.Confirm.ask(
                f"[blue bold]?[/] [bold]Copy singularity images from [blue not bold]$NXF_SINGULARITY_CACHEDIR[/] to the target folder?[/]"
            )

        # Sanity check, for when passed as a cli flag
        if self.singularity_cache_only and self.container != "singularity":
            raise AssertionError("Command has '--singularity-cache-only' set, but '--container' is not 'singularity'")

    def prompt_compression_type(self):
        """Ask user if we should compress the downloaded files"""
        if self.compress_type is None:
            stderr.print(
                "\nIf transferring the downloaded files to another system, it can be convenient to have everything compressed in a single file."
            )
            if self.container == "singularity":
                stderr.print(
                    "[bold]This is [italic]not[/] recommended when downloading Singularity images, as it can take a long time and saves very little space."
                )
            self.compress_type = questionary.select(
                "Choose compression type:",
                choices=[
                    "none",
                    "tar.gz",
                    "tar.bz2",
                    "zip",
                ],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Correct type for no-compression
        if self.compress_type == "none":
            self.compress_type = None

    def download_wf_files(self):
        """Downloads workflow files from GitHub to the :attr:`self.outdir`."""
        log.debug("Downloading {}".format(self.wf_download_url))

        # Download GitHub zip file into memory and extract
        url = requests.get(self.wf_download_url)
        zipfile = ZipFile(BytesIO(url.content))
        zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        gh_name = "{}-{}".format(self.pipeline, self.wf_sha).split("/")[-1]
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
        repl_str = "${projectDir}/../configs/"
        log.debug("Editing 'params.custom_config_base' in '{}'".format(nfconfig_fn))

        # Load the nextflow.config file into memory
        with open(nfconfig_fn, "r") as nfconfig_fh:
            nfconfig = nfconfig_fh.read()

        # Replace the target string
        nfconfig = nfconfig.replace(find_str, repl_str)

        # Append the singularity.cacheDir to the end if we need it
        if self.container == "singularity" and not self.singularity_cache_only:
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

        log.debug("Fetching container names for workflow")
        containers_raw = []

        # Use linting code to parse the pipeline nextflow config
        self.nf_config = nf_core.utils.fetch_wf_config(os.path.join(self.outdir, "workflow"))

        # Find any config variables that look like a container
        for k, v in self.nf_config.items():
            if k.startswith("process.") and k.endswith(".container"):
                containers_raw.append(v.strip('"').strip("'"))

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
                                containers_raw.append(m.strip('"').strip("'"))
                                break
                        # If we get here then we didn't call break - just save the first match
                        else:
                            if len(matches) > 0:
                                containers_raw.append(matches[0].strip('"').strip("'"))

        # Remove duplicates and sort
        containers_raw = sorted(list(set(containers_raw)))

        # Strip any container names that have dynamic names - eg. {params.foo}
        self.containers = []
        for container in containers_raw:
            if "{" in container and "}" in container:
                log.error(
                    f"[red]Container name [green]'{container}'[/] has dynamic Nextflow logic in name - skipping![/]"
                )
                log.info("Please use a 'nextflow run' command to fetch this container. Ask on Slack if you need help.")
            else:
                self.containers.append(container)

        log.info("Found {} container{}".format(len(self.containers), "s" if len(self.containers) > 1 else ""))

    def get_singularity_images(self):
        """Loop through container names and download Singularity images"""

        if len(self.containers) == 0:
            log.info("No container names found in workflow")
        else:
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

                # Exit if we need to pull images and Singularity is not installed
                if len(containers_pull) > 0 and shutil.which("singularity") is None:
                    raise OSError("Singularity is needed to pull images, but it is not installed")

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

    def compress_download(self):
        """Take the downloaded files and make a compressed .tar.gz archive."""
        log.debug("Creating archive: {}".format(self.output_filename))

        # .tar.gz and .tar.bz2 files
        if self.compress_type == "tar.gz" or self.compress_type == "tar.bz2":
            ctype = self.compress_type.split(".")[1]
            with tarfile.open(self.output_filename, "w:{}".format(ctype)) as tar:
                tar.add(self.outdir, arcname=os.path.basename(self.outdir))
            tar_flags = "xzf" if ctype == "gz" else "xjf"
            log.info(f"Command to extract files: [bright_magenta]tar -{tar_flags} {self.output_filename}[/]")

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
            log.info(f"Command to extract files: [bright_magenta]unzip {self.output_filename}[/]")

        # Delete original files
        log.debug(f"Deleting uncompressed files: '{self.outdir}'")
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
            log.info("MD5 checksum for '{}': [blue]{}[/]".format(fname, file_hash))
        else:
            if file_hash == expected:
                log.debug("md5 sum of image matches expected: {}".format(expected))
            else:
                raise IOError("{} md5 does not match remote: {} - {}".format(fname, expected, file_hash))
