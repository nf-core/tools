"""Downloads a nf-core pipeline to the local file system."""

import concurrent.futures
import io
import logging
import os
import re
import shutil
import subprocess
import tarfile
import textwrap
from datetime import datetime
from typing import List, Optional, Tuple
from zipfile import ZipFile

import git
import questionary
import requests
import requests_cache
import rich
import rich.progress
from git.exc import GitCommandError, InvalidGitRepositoryError
from pkg_resources import parse_version as version_parser

import nf_core
import nf_core.list
import nf_core.utils
from nf_core.synced_repo import RemoteProgressbar, SyncedRepo
from nf_core.utils import (
    NFCORE_CACHE_DIR,
    NFCORE_DIR,
    SingularityCacheFilePathValidator,
)

log = logging.getLogger(__name__)
stderr = rich.console.Console(
    stderr=True,
    style="dim",
    highlight=False,
    force_terminal=nf_core.utils.rich_force_colors(),
)


class DownloadError(RuntimeError):
    """A custom exception that is raised when nf-core download encounters a problem that we already took into consideration.
    In this case, we do not want to print the traceback, but give the user some concise, helpful feedback instead.
    """


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


class DownloadWorkflow:
    """Downloads a nf-core workflow from GitHub to the local file system.

    Can also download its Singularity container image if required.

    Args:
        pipeline (str): A nf-core pipeline name.
        revision (List[str]): The workflow revision(s) to download, like `1.0` or `dev` . Defaults to None.
        outdir (str): Path to the local download directory. Defaults to None.
        compress_type (str): Type of compression for the downloaded files. Defaults to None.
        force (bool): Flag to force download even if files already exist (overwrite existing files). Defaults to False.
        platform (bool): Flag to customize the download for Seqera Platform (convert to git bare repo). Defaults to False.
        download_configuration (str): Download the configuration files from nf-core/configs. Defaults to None.
        tag (List[str]): Specify additional tags to add to the downloaded pipeline. Defaults to None.
        container_system (str): The container system to use (e.g., "singularity"). Defaults to None.
        container_library (List[str]): The container libraries (registries) to use. Defaults to None.
        container_cache_utilisation (str): If a local or remote cache of already existing container images should be considered. Defaults to None.
        container_cache_index (str): An index for the remote container cache. Defaults to None.
        parallel_downloads (int): The number of parallel downloads to use. Defaults to 4.
    """

    def __init__(
        self,
        pipeline=None,
        revision=None,
        outdir=None,
        compress_type=None,
        force=False,
        platform=False,
        download_configuration=None,
        additional_tags=None,
        container_system=None,
        container_library=None,
        container_cache_utilisation=None,
        container_cache_index=None,
        parallel_downloads=4,
    ):
        self.pipeline = pipeline
        if isinstance(revision, str):
            self.revision = [revision]
        elif isinstance(revision, tuple):
            self.revision = [*revision]
        else:
            self.revision = []
        self.outdir = outdir
        self.output_filename = None
        self.compress_type = compress_type
        self.force = force
        self.platform = platform
        # if flag is not specified, do not assume deliberate choice and prompt config inclusion interactively.
        # this implies that non-interactive "no" choice is only possible implicitly (e.g. with --platform or if prompt is suppressed by !stderr.is_interactive).
        # only alternative would have been to make it a parameter with argument, e.g. -d="yes" or -d="no".
        self.include_configs = True if download_configuration else False if bool(platform) else None
        # Additional tags to add to the downloaded pipeline. This enables to mark particular commits or revisions with
        # additional tags, e.g. "stable", "testing", "validated", "production" etc. Since this requires a git-repo, it is only
        # available for the bare / Seqera Platform download.
        if isinstance(additional_tags, str) and bool(len(additional_tags)) and self.platform:
            self.additional_tags = [additional_tags]
        elif isinstance(additional_tags, tuple) and bool(len(additional_tags)) and self.platform:
            self.additional_tags = [*additional_tags]
        else:
            self.additional_tags = None
        # Specifying a cache index or container library implies that containers should be downloaded.
        self.container_system = "singularity" if container_cache_index or bool(container_library) else container_system
        # Manually specified container library (registry)
        if isinstance(container_library, str) and bool(len(container_library)):
            self.container_library = [container_library]
        elif isinstance(container_library, tuple) and bool(len(container_library)):
            self.container_library = [*container_library]
        else:
            self.container_library = ["quay.io"]
        # Create a new set and add all values from self.container_library (CLI arguments to --container-library)
        self.registry_set = set(self.container_library) if hasattr(self, "container_library") else set()
        # if a container_cache_index is given, use the file and overrule choice.
        self.container_cache_utilisation = "remote" if container_cache_index else container_cache_utilisation
        self.container_cache_index = container_cache_index
        # allows to specify a container library / registry or a respective mirror to download images from
        self.parallel_downloads = parallel_downloads

        self.wf_revisions = {}
        self.wf_branches = {}
        self.wf_sha = {}
        self.wf_download_url = {}
        self.nf_config = {}
        self.containers = []
        self.containers_remote = []  # stores the remote images provided in the file.

        # Fetch remote workflows
        self.wfs = nf_core.list.Workflows()
        self.wfs.get_remote_workflows()

    def download_workflow(self):
        """Starts a nf-core workflow download."""

        # Get workflow details
        try:
            self.prompt_pipeline_name()
            self.pipeline, self.wf_revisions, self.wf_branches = nf_core.utils.get_repo_releases_branches(
                self.pipeline, self.wfs
            )
            self.prompt_revision()
            self.get_revision_hash()
            # Inclusion of configs is unnecessary for Seqera Platform.
            if not self.platform and self.include_configs is None:
                self.prompt_config_inclusion()
            # If a remote cache is specified, it is safe to assume images should be downloaded.
            if not self.container_cache_utilisation == "remote":
                self.prompt_container_download()
            else:
                self.container_system = "singularity"
            self.prompt_singularity_cachedir_creation()
            self.prompt_singularity_cachedir_utilization()
            self.prompt_singularity_cachedir_remote()
            # Nothing meaningful to compress here.
            if not self.platform:
                self.prompt_compression_type()
        except AssertionError as e:
            raise DownloadError(e) from e

        summary_log = [
            f"Pipeline revision: '{', '.join(self.revision) if len(self.revision) < 5 else self.revision[0]+',['+str(len(self.revision)-2)+' more revisions],'+self.revision[-1]}'",
            f"Use containers: '{self.container_system}'",
        ]
        if self.container_system:
            summary_log.append(f"Container library: '{', '.join(self.container_library)}'")
        if self.container_system == "singularity" and os.environ.get("NXF_SINGULARITY_CACHEDIR") is not None:
            summary_log.append(f"Using [blue]$NXF_SINGULARITY_CACHEDIR[/]': {os.environ['NXF_SINGULARITY_CACHEDIR']}'")
            if self.containers_remote:
                summary_log.append(
                    f"Successfully read {len(self.containers_remote)} containers from the remote '$NXF_SINGULARITY_CACHEDIR' contents."
                )

        # Set an output filename now that we have the outdir
        if self.platform:
            self.output_filename = f"{self.outdir}.git"
            summary_log.append(f"Output file: '{self.output_filename}'")
        elif self.compress_type is not None:
            self.output_filename = f"{self.outdir}.{self.compress_type}"
            summary_log.append(f"Output file: '{self.output_filename}'")
        else:
            summary_log.append(f"Output directory: '{self.outdir}'")

        if not self.platform:
            # Only show entry, if option was prompted.
            summary_log.append(f"Include default institutional configuration: '{self.include_configs}'")
        else:
            summary_log.append(f"Enabled for Seqera Platform: '{self.platform}'")

        # Check that the outdir doesn't already exist
        if os.path.exists(self.outdir):
            if not self.force:
                raise DownloadError(
                    f"Output directory '{self.outdir}' already exists (use [red]--force[/] to overwrite)"
                )
            log.warning(f"Deleting existing output directory: '{self.outdir}'")
            shutil.rmtree(self.outdir)

        # Check that compressed output file doesn't already exist
        if self.output_filename and os.path.exists(self.output_filename):
            if not self.force:
                raise DownloadError(
                    f"Output file '{self.output_filename}' already exists (use [red]--force[/] to overwrite)"
                )
            log.warning(f"Deleting existing output file: '{self.output_filename}'")
            os.remove(self.output_filename)

        # Summary log
        log.info("Saving '{}'\n {}".format(self.pipeline, "\n ".join(summary_log)))

        # Perform the actual download
        if self.platform:
            self.download_workflow_platform()
        else:
            self.download_workflow_static()

    def download_workflow_static(self):
        """Downloads a nf-core workflow from GitHub to the local file system in a self-contained manner."""

        # Download the centralised configs first
        if self.include_configs:
            log.info("Downloading centralised configs from GitHub")
            self.download_configs()

        # Download the pipeline files for each selected revision
        log.info("Downloading workflow files from GitHub")

        for item in zip(self.revision, self.wf_sha.values(), self.wf_download_url.values()):
            revision_dirname = self.download_wf_files(revision=item[0], wf_sha=item[1], download_url=item[2])

            if self.include_configs:
                try:
                    self.wf_use_local_configs(revision_dirname)
                except FileNotFoundError as e:
                    raise DownloadError("Error editing pipeline config file to use local configs!") from e

            # Collect all required singularity images
            if self.container_system == "singularity":
                self.find_container_images(os.path.join(self.outdir, revision_dirname))
                self.gather_registries(os.path.join(self.outdir, revision_dirname))

                try:
                    self.get_singularity_images(current_revision=item[0])
                except OSError as e:
                    raise DownloadError(f"[red]{e}[/]") from e

        # Compress into an archive
        if self.compress_type is not None:
            log.info("Compressing output into archive")
            self.compress_download()

    def download_workflow_platform(self, location=None):
        """Create a bare-cloned git repository of the workflow, so it can be launched with `tw launch` as file:/ pipeline"""

        log.info("Collecting workflow from GitHub")

        self.workflow_repo = WorkflowRepo(
            remote_url=f"https://github.com/{self.pipeline}.git",
            revision=self.revision if self.revision else None,
            commit=self.wf_sha.values() if bool(self.wf_sha) else None,
            additional_tags=self.additional_tags,
            location=(location if location else None),  # manual location is required for the tests to work
            in_cache=False,
        )

        # Remove tags for those revisions that had not been selected
        self.workflow_repo.tidy_tags_and_branches()

        # create a bare clone of the modified repository needed for Seqera Platform
        self.workflow_repo.bare_clone(os.path.join(self.outdir, self.output_filename))

        # extract the required containers
        if self.container_system == "singularity":
            for revision, commit in self.wf_sha.items():
                # Checkout the repo in the current revision
                self.workflow_repo.checkout(commit)
                # Collect all required singularity images
                self.find_container_images(self.workflow_repo.access())
                self.gather_registries(self.workflow_repo.access())

                try:
                    self.get_singularity_images(current_revision=revision)
                except OSError as e:
                    raise DownloadError(f"[red]{e}[/]") from e

        # Justify why compression is skipped for Seqera Platform downloads (Prompt is not shown, but CLI argument could have been set)
        if self.compress_type is not None:
            log.info(
                "Compression choice is ignored for Seqera Platform downloads since nothing can be reasonably compressed."
            )

    def prompt_pipeline_name(self):
        """Prompt for the pipeline name if not set with a flag"""

        if self.pipeline is None:
            stderr.print("Specify the name of a nf-core pipeline or a GitHub repository name (user/repo).")
            self.pipeline = nf_core.utils.prompt_remote_pipeline_name(self.wfs)

    def prompt_revision(self):
        """
        Prompt for pipeline revision / branch
        Prompt user for revision tag if '--revision' was not set
        If --platform is specified, allow to select multiple revisions
        Also the static download allows for multiple revisions, but
        we do not prompt this option interactively.
        """
        if not bool(self.revision):
            (choice, tag_set) = nf_core.utils.prompt_pipeline_release_branch(
                self.wf_revisions, self.wf_branches, multiple=self.platform
            )
            """
            The checkbox() prompt unfortunately does not support passing a Validator,
            so a user who keeps pressing Enter will flounder past the selection without choice.

            bool(choice), bool(tag_set):
            #############################
            True,  True:  A choice was made and revisions were available.
            False, True:  No selection was made, but revisions were available -> defaults to all available.
            False, False: No selection was made because no revisions were available -> raise AssertionError.
            True,  False: Congratulations, you found a bug! That combo shouldn't happen.
            """

            if bool(choice):
                # have to make sure that self.revision is a list of strings, regardless if choice is str or list of strings.
                (self.revision.append(choice) if isinstance(choice, str) else self.revision.extend(choice))
            else:
                if bool(tag_set):
                    self.revision = tag_set
                    log.info("No particular revision was selected, all available will be downloaded.")
                else:
                    raise AssertionError(f"No revisions of {self.pipeline} available for download.")

    def get_revision_hash(self):
        """Find specified revision / branch hash"""

        for revision in self.revision:  # revision is a list of strings, but may be of length 1
            # Branch
            if revision in self.wf_branches.keys():
                self.wf_sha = {**self.wf_sha, revision: self.wf_branches[revision]}

            # Revision
            else:
                for r in self.wf_revisions:
                    if r["tag_name"] == revision:
                        self.wf_sha = {**self.wf_sha, revision: r["tag_sha"]}
                        break

                # Can't find the revisions or branch - throw an error
                else:
                    log.info(
                        "Available {} revisions: '{}'".format(
                            self.pipeline,
                            "', '".join([r["tag_name"] for r in self.wf_revisions]),
                        )
                    )
                    log.info("Available {} branches: '{}'".format(self.pipeline, "', '".join(self.wf_branches.keys())))
                    raise AssertionError(f"Not able to find revision / branch '{revision}' for {self.pipeline}")

        # Set the outdir
        if not self.outdir:
            if len(self.wf_sha) > 1:
                self.outdir = f"{self.pipeline.replace('/', '-').lower()}_{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
            else:
                self.outdir = f"{self.pipeline.replace('/', '-').lower()}_{self.revision[0]}"

        if not self.platform:
            for revision, wf_sha in self.wf_sha.items():
                # Set the download URL and return - only applicable for classic downloads
                self.wf_download_url = {
                    **self.wf_download_url,
                    revision: f"https://github.com/{self.pipeline}/archive/{wf_sha}.zip",
                }

    def prompt_config_inclusion(self):
        """Prompt for inclusion of institutional configurations"""
        if stderr.is_interactive:  # Use rich auto-detection of interactive shells
            self.include_configs = questionary.confirm(
                "Include the nf-core's default institutional configuration files into the download?",
                style=nf_core.utils.nfcore_question_style,
            ).ask()
        else:
            self.include_configs = False
            # do not include by default.

    def prompt_container_download(self):
        """Prompt whether to download container images or not"""

        if self.container_system is None and stderr.is_interactive and not self.platform:
            stderr.print("\nIn addition to the pipeline code, this tool can download software containers.")
            self.container_system = questionary.select(
                "Download software container images:",
                choices=["none", "singularity"],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

    def prompt_singularity_cachedir_creation(self):
        """Prompt about using $NXF_SINGULARITY_CACHEDIR if not already set"""
        if (
            self.container_system == "singularity"
            and os.environ.get("NXF_SINGULARITY_CACHEDIR") is None
            and stderr.is_interactive  # Use rich auto-detection of interactive shells
        ):
            stderr.print(
                "\nNextflow and nf-core can use an environment variable called [blue]$NXF_SINGULARITY_CACHEDIR[/] that is a path to a directory where remote Singularity images are stored. "
                "This allows downloaded images to be cached in a central location."
            )
            if rich.prompt.Confirm.ask(
                "[blue bold]?[/] [bold]Define [blue not bold]$NXF_SINGULARITY_CACHEDIR[/] for a shared Singularity image download folder?[/]"
            ):
                if not self.container_cache_index:
                    self.container_cache_utilisation == "amend"  # retain "remote" choice.
                # Prompt user for a cache directory path
                cachedir_path = None
                while cachedir_path is None:
                    prompt_cachedir_path = questionary.path(
                        "Specify the path:",
                        only_directories=True,
                        style=nf_core.utils.nfcore_question_style,
                    ).unsafe_ask()
                    cachedir_path = os.path.abspath(os.path.expanduser(prompt_cachedir_path))
                    if prompt_cachedir_path == "":
                        log.error("Not using [blue]$NXF_SINGULARITY_CACHEDIR[/]")
                        cachedir_path = False
                    elif not os.path.isdir(cachedir_path):
                        log.error(f"'{cachedir_path}' is not a directory.")
                        cachedir_path = None
                if cachedir_path:
                    os.environ["NXF_SINGULARITY_CACHEDIR"] = cachedir_path

                    """
                    Optionally, create a permanent entry for the NXF_SINGULARITY_CACHEDIR in the terminal profile.
                    Currently support for bash and zsh.
                    ToDo: "sh", "dash", "ash","csh", "tcsh", "ksh", "fish", "cmd", "powershell", "pwsh"?
                    """

                    if os.getenv("SHELL", "") == "/bin/bash":
                        shellprofile_path = os.path.expanduser("~/~/.bash_profile")
                        if not os.path.isfile(shellprofile_path):
                            shellprofile_path = os.path.expanduser("~/.bashrc")
                            if not os.path.isfile(shellprofile_path):
                                shellprofile_path = False
                    elif os.getenv("SHELL", "") == "/bin/zsh":
                        shellprofile_path = os.path.expanduser("~/.zprofile")
                        if not os.path.isfile(shellprofile_path):
                            shellprofile_path = os.path.expanduser("~/.zshenv")
                            if not os.path.isfile(shellprofile_path):
                                shellprofile_path = False
                    else:
                        shellprofile_path = os.path.expanduser("~/.profile")
                        if not os.path.isfile(shellprofile_path):
                            shellprofile_path = False

                    if shellprofile_path:
                        stderr.print(
                            f"\nSo that [blue]$NXF_SINGULARITY_CACHEDIR[/] is always defined, you can add it to your [blue not bold]~/{os.path.basename(shellprofile_path)}[/] file ."
                            "This will then be automatically set every time you open a new terminal. We can add the following line to this file for you: \n"
                            f'[blue]export NXF_SINGULARITY_CACHEDIR="{cachedir_path}"[/]'
                        )
                        append_to_file = rich.prompt.Confirm.ask(
                            f"[blue bold]?[/] [bold]Add to [blue not bold]~/{os.path.basename(shellprofile_path)}[/] ?[/]"
                        )
                        if append_to_file:
                            with open(os.path.expanduser(shellprofile_path), "a") as f:
                                f.write(
                                    "\n\n#######################################\n"
                                    f"## Added by `nf-core download` v{nf_core.__version__} ##\n"
                                    + f'export NXF_SINGULARITY_CACHEDIR="{cachedir_path}"'
                                    + "\n#######################################\n"
                                )
                            log.info(f"Successfully wrote to [blue]{shellprofile_path}[/]")
                            log.warning(
                                "You will need reload your terminal after the download completes for this to take effect."
                            )

    def prompt_singularity_cachedir_utilization(self):
        """Ask if we should *only* use $NXF_SINGULARITY_CACHEDIR without copying into target"""
        if (
            self.container_cache_utilisation is None  # no choice regarding singularity cache has been made.
            and self.container_system == "singularity"
            and os.environ.get("NXF_SINGULARITY_CACHEDIR") is not None
            and stderr.is_interactive
        ):
            stderr.print(
                "\nIf you are working on the same system where you will run Nextflow, you can amend the downloaded images to the ones in the"
                "[blue not bold]$NXF_SINGULARITY_CACHEDIR[/] folder, Nextflow will automatically find them. "
                "However if you will transfer the downloaded files to a different system then they should be copied to the target folder."
            )
            self.container_cache_utilisation = questionary.select(
                "Copy singularity images from $NXF_SINGULARITY_CACHEDIR to the target folder or amend new images to the cache?",
                choices=["amend", "copy"],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

    def prompt_singularity_cachedir_remote(self):
        """Prompt about the index of a remote $NXF_SINGULARITY_CACHEDIR"""
        if (
            self.container_system == "singularity"
            and self.container_cache_utilisation == "remote"
            and self.container_cache_index is None
            and stderr.is_interactive  # Use rich auto-detection of interactive shells
        ):
            # Prompt user for a file listing the contents of the remote cache directory
            cachedir_index = None
            while cachedir_index is None:
                prompt_cachedir_index = questionary.path(
                    "Specify a list of the container images that are already present on the remote system:",
                    validate=SingularityCacheFilePathValidator,
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()
                cachedir_index = os.path.abspath(os.path.expanduser(prompt_cachedir_index))
                if prompt_cachedir_index == "":
                    log.error("Will disregard contents of a remote [blue]$NXF_SINGULARITY_CACHEDIR[/]")
                    self.container_cache_index = None
                    self.container_cache_utilisation = "copy"
                elif not os.access(cachedir_index, os.R_OK):
                    log.error(f"'{cachedir_index}' is not a readable file.")
                    cachedir_index = None
            if cachedir_index:
                self.container_cache_index = cachedir_index
        # in any case read the remote containers, even if no prompt was shown.
        self.read_remote_containers()

    def read_remote_containers(self):
        """Reads the file specified as index for the remote Singularity cache dir"""
        if (
            self.container_system == "singularity"
            and self.container_cache_utilisation == "remote"
            and self.container_cache_index is not None
        ):
            n_total_images = 0
            try:
                with open(self.container_cache_index) as indexfile:
                    for line in indexfile.readlines():
                        match = re.search(r"([^\/\\]+\.img)", line, re.S)
                        if match:
                            n_total_images += 1
                            self.containers_remote.append(match.group(0))
                    if n_total_images == 0:
                        raise LookupError("Could not find valid container names in the index file.")
                    self.containers_remote = sorted(list(set(self.containers_remote)))
            except (FileNotFoundError, LookupError) as e:
                log.error(f"[red]Issue with reading the specified remote $NXF_SINGULARITY_CACHE index:[/]\n{e}\n")
                if stderr.is_interactive and rich.prompt.Confirm.ask("[blue]Specify a new index file and try again?"):
                    self.container_cache_index = None  # reset chosen path to index file.
                    self.prompt_singularity_cachedir_remote()
                else:
                    log.info("Proceeding without consideration of the remote $NXF_SINGULARITY_CACHE index.")
                    self.container_cache_index = None
                    if os.environ.get("NXF_SINGULARITY_CACHEDIR"):
                        self.container_cache_utilisation = "copy"  # default to copy if possible, otherwise skip.
                    else:
                        self.container_cache_utilisation = None

    def prompt_compression_type(self):
        """Ask user if we should compress the downloaded files"""
        if self.compress_type is None:
            stderr.print(
                "\nIf transferring the downloaded files to another system, it can be convenient to have everything compressed in a single file."
            )
            if self.container_system == "singularity":
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

    def download_wf_files(self, revision, wf_sha, download_url):
        """Downloads workflow files from GitHub to the :attr:`self.outdir`."""
        log.debug(f"Downloading {download_url}")

        # Download GitHub zip file into memory and extract
        url = requests.get(download_url)
        with ZipFile(io.BytesIO(url.content)) as zipfile:
            zipfile.extractall(self.outdir)

        # create a filesystem-safe version of the revision name for the directory
        revision_dirname = re.sub("[^0-9a-zA-Z]+", "_", revision)
        # account for name collisions, if there is a branch / release named "configs" or "singularity-images"
        if revision_dirname in ["configs", "singularity-images"]:
            revision_dirname = re.sub("[^0-9a-zA-Z]+", "_", self.pipeline + revision_dirname)

        # Rename the internal directory name to be more friendly
        gh_name = f"{self.pipeline}-{wf_sha if bool(wf_sha) else ''}".split("/")[-1]
        os.rename(
            os.path.join(self.outdir, gh_name),
            os.path.join(self.outdir, revision_dirname),
        )

        # Make downloaded files executable
        for dirpath, _, filelist in os.walk(os.path.join(self.outdir, revision_dirname)):
            for fname in filelist:
                os.chmod(os.path.join(dirpath, fname), 0o775)

        return revision_dirname

    def download_configs(self):
        """Downloads the centralised config profiles from nf-core/configs to :attr:`self.outdir`."""
        configs_zip_url = "https://github.com/nf-core/configs/archive/master.zip"
        configs_local_dir = "configs-master"
        log.debug(f"Downloading {configs_zip_url}")

        # Download GitHub zip file into memory and extract
        url = requests.get(configs_zip_url)
        with ZipFile(io.BytesIO(url.content)) as zipfile:
            zipfile.extractall(self.outdir)

        # Rename the internal directory name to be more friendly
        os.rename(
            os.path.join(self.outdir, configs_local_dir),
            os.path.join(self.outdir, "configs"),
        )

        # Make downloaded files executable
        for dirpath, _, filelist in os.walk(os.path.join(self.outdir, "configs")):
            for fname in filelist:
                os.chmod(os.path.join(dirpath, fname), 0o775)

    def wf_use_local_configs(self, revision_dirname):
        """Edit the downloaded nextflow.config file to use the local config files"""
        nfconfig_fn = os.path.join(self.outdir, revision_dirname, "nextflow.config")
        find_str = "https://raw.githubusercontent.com/nf-core/configs/${params.custom_config_version}"
        repl_str = "${projectDir}/../configs/"
        log.debug(f"Editing 'params.custom_config_base' in '{nfconfig_fn}'")

        # Load the nextflow.config file into memory
        with open(nfconfig_fn) as nfconfig_fh:
            nfconfig = nfconfig_fh.read()

        # Replace the target string
        log.debug(f"Replacing '{find_str}' with '{repl_str}'")
        nfconfig = nfconfig.replace(find_str, repl_str)

        # Append the singularity.cacheDir to the end if we need it
        if self.container_system == "singularity" and self.container_cache_utilisation == "copy":
            nfconfig += (
                f"\n\n// Added by `nf-core download` v{nf_core.__version__} //\n"
                + 'singularity.cacheDir = "${projectDir}/../singularity-images/"'
                + "\n///////////////////////////////////////"
            )

        # Write the file out again
        log.debug(f"Updating '{nfconfig_fn}'")
        with open(nfconfig_fn, "w") as nfconfig_fh:
            nfconfig_fh.write(nfconfig)

    def find_container_images(self, workflow_directory):
        """Find container image names for workflow.

        Starts by using `nextflow config` to pull out any process.container
        declarations. This works for DSL1. It should return a simple string with resolved logic,
        but not always, e.g. not for differentialabundance 1.2.0

        Second, we look for DSL2 containers. These can't be found with
        `nextflow config` at the time of writing, so we scrape the pipeline files.
        This returns raw matches that will likely need to be cleaned.
        """

        log.debug("Fetching container names for workflow")
        # since this is run for multiple revisions now, account for previously detected containers.
        previous_findings = [] if not self.containers else self.containers
        config_findings = []
        module_findings = []

        # Use linting code to parse the pipeline nextflow config
        self.nf_config = nf_core.utils.fetch_wf_config(workflow_directory)

        # Find any config variables that look like a container
        for k, v in self.nf_config.items():
            if (k.startswith("process.") or k.startswith("params.")) and k.endswith(".container"):
                """
                Can be plain string / Docker URI or DSL2 syntax

                Since raw parsing is done by Nextflow, single quotes will be (partially) escaped in DSL2.
                Use cleaning regex on DSL2. Same as for modules, except that (?<![\\]) ensures that escaped quotes are ignored.
                """

                # for DSL2 syntax in process scope of configs
                config_regex = re.compile(
                    r"[\\s{}=$]*(?P<quote>(?<![\\])[\'\"])(?P<param>(?:.(?!(?<![\\])\1))*.?)\1[\\s}]*"
                )
                config_findings_dsl2 = re.findall(config_regex, v)

                if bool(config_findings_dsl2):
                    # finding will always be a tuple of length 2, first the quote used and second the enquoted value.
                    for finding in config_findings_dsl2:
                        config_findings.append(finding + (self.nf_config, "Nextflow configs"))
                else:  # no regex match, likely just plain string
                    """
                    Append string also as finding-like tuple for consistency
                    because all will run through rectify_raw_container_matches()
                    self.nf_config is needed, because we need to restart search over raw input
                    if no proper container matches are found.
                    """
                    config_findings.append((k, v.strip('"').strip("'"), self.nf_config, "Nextflow configs"))

        # rectify the container paths found in the config
        # Raw config_findings may yield multiple containers, so better create a shallow copy of the list, since length of input and output may be different ?!?
        config_findings = self.rectify_raw_container_matches(config_findings[:])

        # Recursive search through any DSL2 module files for container spec lines.
        for subdir, _, files in os.walk(os.path.join(workflow_directory, "modules")):
            for file in files:
                if file.endswith(".nf"):
                    file_path = os.path.join(subdir, file)
                    with open(file_path) as fh:
                        # Look for any lines with container "xxx" or container 'xxx'
                        search_space = fh.read()
                        """
                        Figure out which quotes were used and match everything until the closing quote.
                        Since the other quote typically appears inside, a simple r"container\\s*[\"\']([^\"\']*)[\"\']" unfortunately abridges the matches.

                        container\\s+[\\s{}$=]* matches the literal word "container" followed by whitespace, brackets, equal or variable names.
                        (?P<quote>[\'\"]) The quote character is captured into the quote group \1.
                        The pattern (?:.(?!\1))*.? is used to match any character (.) not followed by the closing quote character (?!\1).
                        This capture happens greedy *, but we add a .? to ensure that we don't match the whole file until the last occurrence
                        of the closing quote character, but rather stop at the first occurrence. \1 inserts the matched quote character into the regex, either " or '.
                        It may be followed by whitespace or closing bracket [\\s}]*
                        re.DOTALL is used to account for the string to be spread out across multiple lines.
                        """
                        container_regex = re.compile(
                            r"container\s+[\\s{}=$]*(?P<quote>[\'\"])(?P<param>(?:.(?!\1))*.?)\1[\\s}]*",
                            re.DOTALL,
                        )

                        local_module_findings = re.findall(container_regex, search_space)

                        # finding fill always be a tuple of length 2, first the quote used and second the enquoted value.
                        for finding in local_module_findings:
                            # append finding since we want to collect them from all modules
                            # also append search_space because we need to start over later if nothing was found.
                            module_findings.append(finding + (search_space, file_path))

        # Not sure if there will ever be multiple container definitions per module, but beware DSL3.
        # Like above run on shallow copy, because length may change at runtime.
        module_findings = self.rectify_raw_container_matches(module_findings[:])

        # Again clean list, in case config declares Docker URI but module or previous finding already had the http:// download
        self.containers = self.prioritize_direct_download(previous_findings + config_findings + module_findings)

    def rectify_raw_container_matches(self, raw_findings):
        """Helper function to rectify the raw extracted container matches into fully qualified container names.
        If multiple containers are found, any prefixed with http for direct download is prioritized

        Example syntax:

        Early DSL2:

        .. code-block:: groovy

            if (workflow.containerEngine == 'singularity' && !params.singularity_pull_docker_container) {
                container "https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0"
            } else {
                container "quay.io/biocontainers/fastqc:0.11.9--0"
            }

        Later DSL2:

        .. code-block:: groovy

            container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
                'https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0' :
                'biocontainers/fastqc:0.11.9--0' }"

        Later DSL2, variable is being used:

        .. code-block:: groovy

            container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
                "https://depot.galaxyproject.org/singularity/${container_id}" :
                "quay.io/biocontainers/${container_id}" }"

            container_id = 'mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:afaaa4c6f5b308b4b6aa2dd8e99e1466b2a6b0cd-0'

        DSL1 / Special case DSL2:

        .. code-block:: groovy

            container "nfcore/cellranger:6.0.2"

        """
        cleaned_matches = []

        # Thanks Stack Overflow for the regex: https://stackoverflow.com/a/3809435/713980
        url_regex = (
            r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        )
        # Thanks Stack Overflow for the regex: https://stackoverflow.com/a/39672069/713980
        docker_regex = r"^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$"

        # at this point, we don't have to distinguish anymore, because we will later prioritize direct downloads over Docker URIs.
        either_url_or_docker = re.compile(f"{url_regex}|{docker_regex}", re.S)

        for _, container_value, search_space, file_path in raw_findings:
            """
            Now we need to isolate all container paths (typically quoted strings) from the raw container_value

            For example from:

            "${ workflow.containerEngine == \'singularity\' && !task.ext.singularity_pull_docker_container ?
            \'https://depot.galaxyproject.org/singularity/ubuntu:20.04\' :
            \'nf-core/ubuntu:20.04\' }"

            we want to extract

            'singularity'
            'https://depot.galaxyproject.org/singularity/ubuntu:20.04'
            'nf-core/ubuntu:20.04'

            The problem is, that we find almost arbitrary notations in container_value,
            such as single quotes, double quotes and escaped single quotes

            Sometimes target strings are wrapped into a variable to be evaluated by Nextflow,
            like in the example above.
            Sometimes the whole string is a variable "${container_name}", that is
            denoted elsewhere.

            Sometimes the string contains variables which may be defined elsewhere or
            not even known when downloading, like ${params.genome}.

            "https://depot.galaxyproject.org/singularity/ubuntu:${version}" or
            "nfcore/sarekvep:dev.${params.genome}"

            Mostly, it is a nested DSL2 string, but it may also just be a plain string.


            First, check if container_value is a plain container URI like in DSL1 pipelines
            or a plain URL like in the old DSL2 convention

            """
            direct_match = re.match(either_url_or_docker, container_value.strip())
            if direct_match:
                cleaned_matches.append(direct_match.group(0))
                continue  # oh yes, that was plain sailing

            """
            no plain string, we likely need to break it up further

            [^\"\'] makes sure that the outermost quote character is not matched.
            (?P<quote>(?<![\\])[\'\"]) again captures the quote character, but not if it is preceded by an escape sequence (?<![\\])
            (?P<param>(?:.(?!(?<![\\])\1))*.?)\1 is basically what I used above, but again has the (?<![\\]) inserted before \1 to account for escapes.
            """

            container_value_defs = re.findall(
                r"[^\"\'](?P<quote>(?<![\\])[\'\"])(?P<param>(?:.(?!(?<![\\])\1))*.?)\1",
                container_value,
            )

            """
            eliminate known false positives and create plain list out of the tuples returned by the regex above
            example result:
            ['https://depot.galaxyproject.org/singularity/scanpy:1.7.2--pyhdfd78af_0', 'biocontainers/scanpy:1.7.2--pyhdfd78af_0']
            """
            container_value_defs = [
                capture for _, capture in container_value_defs[:] if capture not in ["singularity", "apptainer"]
            ]

            """
            For later DSL2 syntax, container_value_defs should contain both, the download URL and the Docker URI.
            For earlier DSL2, both end up in different raw_findings, so a subsequent deduplication is necessary anyway
            to not pull a container that is already downloaded directly.

            At this point, we just add everything that is either a URL or a Docker URI to cleaned matches.
            """

            valid_containers = list(filter(either_url_or_docker.match, container_value_defs))

            if valid_containers:
                cleaned_matches = cleaned_matches + valid_containers
                # Yeah, we have successfully extracted something from this raw_finding, so move on.
                continue

            """
            Neither a plain Docker URI nor a DSL2-like definition was found. This is a tricky case, then.

            Some modules declare the container as separate variable. This entails that " instead of ' is used,
            so container_value will not contain it.

            Therefore, we need to repeat the search over the raw contents, extract the variable name, and use it inside a new regex.
            This is why the raw search_space is still needed at this level.

            To get the variable name ( ${container_id} in above example ), we match the literal word "container" and use lookbehind (reset the match).
            Then we skip [^${}]+ everything that is not $ or curly braces. The next capture group is
            ${ followed by any characters that are not curly braces [^{}]+ and ended by a closing curly brace (}),
            but only if it's not followed by any other curly braces (?![^{]*}). The latter ensures we capture the innermost
            variable name.
            """

            container_definition = re.search(r"(?<=container)[^\${}]+\${([^{}]+)}(?![^{]*})", str(search_space))

            if bool(container_definition) and bool(container_definition.group(1)):
                pattern = re.escape(container_definition.group(1))
                # extract the quoted string(s) following the variable assignment
                container_names = re.findall(rf"{pattern}\s*=\s*[\"\']([^\"\']+)[\"\']", search_space)

                if bool(container_names):
                    if isinstance(container_names, str):
                        cleaned_matches.append(f"https://depot.galaxyproject.org/singularity/{container_names}")

                    elif isinstance(container_names, list):
                        # this deliberately appends container_names[-1] twice to cleaned_matches
                        # but deduplication is performed anyway and just setting this_container
                        # here as well allows for an easy check to see if parsing succeeded.
                        for container_name in container_names:
                            cleaned_matches.append(f"https://depot.galaxyproject.org/singularity/{container_name}")

                    continue

            # all implemented options exhausted. Nothing left to be done:
            log.error(
                f"[red]Cannot parse container string in '{file_path}':\n\n{textwrap.indent(container_value, '    ')}\n\n:warning: Skipping this singularity image."
            )

        """
        Loop has finished, now we need to remove duplicates and prioritize direct downloads over containers pulled from the registries
        """
        return self.prioritize_direct_download(cleaned_matches)

    def prioritize_direct_download(self, container_list):
        """
        Helper function that takes a list of container images (URLs and Docker URIs),
        eliminates all Docker URIs for which also a URL is contained and returns the
        cleaned and also deduplicated list.

        Conceptually, this works like so:

        Everything after the last Slash should be identical, e.g. "scanpy:1.7.2--pyhdfd78af_0" in
        ['https://depot.galaxyproject.org/singularity/scanpy:1.7.2--pyhdfd78af_0', 'biocontainers/scanpy:1.7.2--pyhdfd78af_0']


        re.sub('.*/(.*)','\\1',c) will drop everything up to the last slash from c (container_id)

        d.get(k:=re.sub('.*/(.*)','\\1',c),'') assigns the truncated string to k (key) and gets the
        corresponding value from the dict if present or else defaults to "".

        If the regex pattern matches, the original container_id will be assigned to the dict with the k key.
        r"^$|(?!^http)" matches an empty string (we didn't have it in the dict yet and want to keep it in either case) or
        any string that does not start with http. Because if our current dict value already starts with http,
        we want to keep it and not replace with with whatever we have now (which might be the Docker URI).

        A regex that matches http, r"^$|^http" could thus be used to prioritize the Docker URIs over http Downloads
        """
        d = {}
        for c in container_list:
            if re.match(r"^$|(?!^http)", d.get(k := re.sub(".*/(.*)", "\\1", c), "")):
                log.debug(f"{c} matches and will be saved as {k}")
                d[k] = c
        return sorted(list(d.values()))

    def gather_registries(self, workflow_directory: str) -> None:
        """Fetch the registries from the pipeline config and CLI arguments and store them in a set.
        This is needed to symlink downloaded container images so Nextflow will find them.
        """

        # should exist, because find_container_images() is always called before
        if not self.nf_config:
            self.nf_config = nf_core.utils.fetch_wf_config(workflow_directory)

        # Select registries defined in pipeline config
        configured_registries = [
            "apptainer.registry",
            "docker.registry",
            "podman.registry",
            "singularity.registry",
        ]

        for registry in configured_registries:
            if registry in self.nf_config:
                self.registry_set.add(self.nf_config[registry])

        # add depot.galaxyproject.org to the set, because it is the default registry for singularity hardcoded in modules
        self.registry_set.add("depot.galaxyproject.org")

    def symlink_singularity_images(self, image_out_path: str) -> None:
        """Create a symlink for each registry in the registry set that points to the image.
        We have dropped the explicit registries from the modules in favor of the configurable registries.
        Unfortunately, Nextflow still expects the registry to be part of the file name, so a symlink is needed.

        The base image, e.g. ./nf-core-gatk-4.4.0.0.img will thus be symlinked as for example ./quay.io-nf-core-gatk-4.4.0.0.img
        by prepending all registries in self.registry_set to the image name.

        Unfortunately, out output image name may contain a registry definition (Singularity image pulled from depot.galaxyproject.org
        or older pipeline version, where the docker registry was part of the image name in the modules). Hence, it must be stripped
        before to ensure that it is really the base name.
        """

        if self.registry_set:
            # Create a regex pattern from the set, in case trimming is needed.
            trim_pattern = "|".join(f"^{re.escape(registry)}-?" for registry in self.registry_set)

            for registry in self.registry_set:
                if not os.path.basename(image_out_path).startswith(registry):
                    symlink_name = os.path.join("./", f"{registry}-{os.path.basename(image_out_path)}")
                else:
                    trimmed_name = re.sub(f"{trim_pattern}", "", os.path.basename(image_out_path))
                    symlink_name = os.path.join("./", f"{registry}-{trimmed_name}")

                symlink_full = os.path.join(os.path.dirname(image_out_path), symlink_name)
                target_name = os.path.join("./", os.path.basename(image_out_path))

                if not os.path.exists(symlink_full) and target_name != symlink_name:
                    os.makedirs(os.path.dirname(symlink_full), exist_ok=True)
                    image_dir = os.open(os.path.dirname(image_out_path), os.O_RDONLY)
                    try:
                        os.symlink(
                            target_name,
                            symlink_name,
                            dir_fd=image_dir,
                        )
                        log.debug(f"Symlinked {target_name} as {symlink_name}.")
                    finally:
                        os.close(image_dir)

    def get_singularity_images(self, current_revision: str = "") -> None:
        """Loop through container names and download Singularity images"""

        if len(self.containers) == 0:
            log.info("No container names found in workflow")
        else:
            log.info(
                f"Processing workflow revision {current_revision}, found {len(self.containers)} container image{'s' if len(self.containers) > 1 else ''} in total."
            )

            with DownloadProgress() as progress:
                task = progress.add_task(
                    "Collecting container images",
                    total=len(self.containers),
                    progress_type="summary",
                )

                # Organise containers based on what we need to do with them
                containers_exist: List[str] = []
                containers_cache: List[Tuple[str, str, Optional[str]]] = []
                containers_download: List[Tuple[str, str, Optional[str]]] = []
                containers_pull: List[Tuple[str, str, Optional[str]]] = []
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

                    # We already have the target file in place or in remote cache, return
                    if os.path.exists(out_path) or os.path.basename(out_path) in self.containers_remote:
                        containers_exist.append(container)
                        continue

                    # We have a copy of this in the NXF_SINGULARITY_CACHE dir
                    if cache_path and os.path.exists(cache_path):
                        containers_cache.append((container, out_path, cache_path))
                        continue

                    # Direct download within Python
                    if container.startswith("http"):
                        containers_download.append((container, out_path, cache_path))
                        continue

                    # Pull using singularity
                    containers_pull.append((container, out_path, cache_path))

                # Exit if we need to pull images and Singularity is not installed
                if len(containers_pull) > 0:
                    if not (shutil.which("singularity") or shutil.which("apptainer")):
                        raise OSError(
                            "Singularity/Apptainer is needed to pull images, but it is not installed or not in $PATH"
                        )

                if containers_exist:
                    if self.container_cache_index is not None:
                        log.info(
                            f"{len(containers_exist)} containers are already cached remotely and won't be retrieved."
                        )
                    # Go through each method of fetching containers in order
                    for container in containers_exist:
                        progress.update(task, description="Image file exists at destination")
                        progress.update(task, advance=1)

                if containers_cache:
                    for container in containers_cache:
                        progress.update(task, description="Copying singularity images from cache")
                        self.singularity_copy_cache_image(*container)
                        progress.update(task, advance=1)

                if containers_download or containers_pull:
                    # if clause gives slightly better UX, because Download is no longer displayed if nothing is left to be downloaded.
                    with concurrent.futures.ThreadPoolExecutor(max_workers=self.parallel_downloads) as pool:
                        progress.update(task, description="Downloading singularity images")

                        # Kick off concurrent downloads
                        future_downloads = [
                            pool.submit(self.singularity_download_image, *containers, progress)
                            for containers in containers_download
                        ]

                        # Make ctrl-c work with multi-threading
                        self.kill_with_fire = False

                        try:
                            # Iterate over each threaded download, waiting for them to finish
                            for future in concurrent.futures.as_completed(future_downloads):
                                future.result()
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

                    for containers in containers_pull:
                        progress.update(task, description="Pulling singularity images")
                        # it is possible to try multiple registries / mirrors if multiple were specified.
                        # Iteration happens over a copy of self.container_library[:], as I want to be able to remove failing registries for subsequent images.
                        for library in self.container_library[:]:
                            try:
                                self.singularity_pull_image(*containers, library, progress)
                                # Pulling the image was successful, no ContainerError was raised, break the library loop
                                break
                            except ContainerError.ImageExistsError:
                                # Pulling not required
                                break
                            except ContainerError.RegistryNotFoundError as e:
                                self.container_library.remove(library)
                                # The only library was removed
                                if not self.container_library:
                                    log.error(e.message)
                                    log.error(e.helpmessage)
                                    raise OSError from e
                                else:
                                    # Other libraries can be used
                                    continue
                            except ContainerError.ImageNotFoundError as e:
                                # Try other registries
                                if e.error_log.absolute_URI:
                                    break  # there no point in trying other registries if absolute URI was specified.
                                else:
                                    continue
                            except ContainerError.InvalidTagError:
                                # Try other registries
                                continue
                            except ContainerError.OtherError as e:
                                # Try other registries
                                log.error(e.message)
                                log.error(e.helpmessage)
                                if e.error_log.absolute_URI:
                                    break  # there no point in trying other registries if absolute URI was specified.
                                else:
                                    continue
                        else:
                            # The else clause executes after the loop completes normally.
                            # This means the library loop completed without breaking, indicating failure for all libraries (registries)
                            log.error(
                                f"Not able to pull image of {containers}. Service might be down or internet connection is dead."
                            )
                        # Task should advance in any case. Failure to pull will not kill the download process.
                        progress.update(task, advance=1)

    def singularity_image_filenames(self, container: str) -> Tuple[str, Optional[str]]:
        """Check Singularity cache for image, copy to destination folder if found.

        Args:
            container (str):    A pipeline's container name. Can be direct download URL
                                or a Docker Hub repository ID.

        Returns:
            tuple (str, str):   Returns a tuple of (out_path, cache_path).
                                out_path is the final target output path. it may point to the NXF_SINGULARITY_CACHEDIR, if cache utilisation was set to 'amend'.
                                If cache utilisation was set to 'copy', it will point to the target folder, a subdirectory of the output directory. In the latter case,
                                cache_path may either be None (image is not yet cached locally) or point to the image in the NXF_SINGULARITY_CACHEDIR, so it will not be
                                downloaded from the web again, but directly copied from there. See get_singularity_images() for implementation.
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

        # Trim potential registries from the name for consistency.
        # This will allow pipelines to work offline without symlinked images,
        # if docker.registry / singularity.registry are set to empty strings at runtime, which can be included in the HPC config profiles easily.
        if self.registry_set:
            # Create a regex pattern from the set of registries
            trim_pattern = "|".join(f"^{re.escape(registry)}-?" for registry in self.registry_set)
            # Use the pattern to trim the string
            out_name = re.sub(f"{trim_pattern}", "", out_name)

        # Full destination and cache paths
        out_path = os.path.abspath(os.path.join(self.outdir, "singularity-images", out_name))
        cache_path = None
        if os.environ.get("NXF_SINGULARITY_CACHEDIR"):
            cache_path = os.path.join(os.environ["NXF_SINGULARITY_CACHEDIR"], out_name)
            # Use only the cache - set this as the main output path
            if self.container_cache_utilisation == "amend":
                out_path = cache_path
                cache_path = None
        elif self.container_cache_utilisation in ["amend", "copy"]:
            raise FileNotFoundError("Singularity cache is required but no '$NXF_SINGULARITY_CACHEDIR' set!")

        return (out_path, cache_path)

    def singularity_copy_cache_image(self, container: str, out_path: str, cache_path: Optional[str]) -> None:
        """Copy Singularity image from NXF_SINGULARITY_CACHEDIR to target folder."""
        # Copy to destination folder if we have a cached version
        if cache_path and os.path.exists(cache_path):
            log.debug(f"Copying {container} from cache: '{os.path.basename(out_path)}'")
            shutil.copyfile(cache_path, out_path)
            # Create symlinks to ensure that the images are found even with different registries being used.
            self.symlink_singularity_images(out_path)

    def singularity_download_image(
        self, container: str, out_path: str, cache_path: Optional[str], progress: DownloadProgress
    ) -> None:
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
                    for data in r.iter_content(chunk_size=io.DEFAULT_BUFFER_SIZE):
                        # Check that the user didn't hit ctrl-c
                        if self.kill_with_fire:
                            raise KeyboardInterrupt
                        progress.update(task, advance=len(data))
                        fh.write(data)

            # Rename partial filename to final filename
            os.rename(output_path_tmp, output_path)

            # Copy cached download if we are using the cache
            if cache_path:
                log.debug(f"Copying {container} from cache: '{os.path.basename(out_path)}'")
                progress.update(task, description="Copying from cache to target directory")
                shutil.copyfile(cache_path, out_path)

            # Create symlinks to ensure that the images are found even with different registries being used.
            self.symlink_singularity_images(output_path)

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
        finally:
            del output_path_tmp

    def singularity_pull_image(
        self, container: str, out_path: str, cache_path: Optional[str], library: List[str], progress: DownloadProgress
    ) -> None:
        """Pull a singularity image using ``singularity pull``

        Attempt to use a local installation of singularity to pull the image.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``nfcore/name:version``.
            library (list of str): A list of libraries to try for pulling the image.

        Raises:
            Various exceptions possible from `subprocess` execution of Singularity.
        """
        output_path = cache_path or out_path

        # where the output of 'singularity pull' is first generated before being copied to the NXF_SINGULARITY_CACHDIR.
        # if not defined by the Singularity administrators, then use the temporary directory to avoid storing the images in the work directory.
        if os.environ.get("SINGULARITY_CACHEDIR") is None:
            os.environ["SINGULARITY_CACHEDIR"] = NFCORE_CACHE_DIR

        # Sometimes, container still contain an explicit library specification, which
        # resulted in attempted pulls e.g. from docker://quay.io/quay.io/qiime2/core:2022.11
        # Thus, if an explicit registry is specified, the provided -l value is ignored.
        container_parts = container.split("/")
        if len(container_parts) > 2:
            address = f"docker://{container}"
            absolute_URI = True
        else:
            address = f"docker://{library}/{container.replace('docker://', '')}"
            absolute_URI = False

        if shutil.which("singularity"):
            singularity_command = [
                "singularity",
                "pull",
                "--name",
                output_path,
                address,
            ]
        elif shutil.which("apptainer"):
            singularity_command = ["apptainer", "pull", "--name", output_path, address]
        else:
            raise OSError("Singularity/Apptainer is needed to pull images, but it is not installed or not in $PATH")
        log.debug(f"Building singularity image: {address}")
        log.debug(f"Singularity command: {' '.join(singularity_command)}")

        # Progress bar to show that something is happening
        task = progress.add_task(
            container,
            start=False,
            total=False,
            progress_type="singularity_pull",
            current_log="",
        )

        # Run the singularity pull command
        with subprocess.Popen(
            singularity_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        ) as proc:
            lines = []
            if proc.stdout is not None:
                for line in proc.stdout:
                    lines.append(line)
                    progress.update(task, current_log=line.strip())

        if lines:
            # something went wrong with the container retrieval
            if any("FATAL: " in line for line in lines):
                progress.remove_task(task)
                raise ContainerError(
                    container=container,
                    registry=library,
                    address=address,
                    absolute_URI=absolute_URI,
                    out_path=out_path if out_path else cache_path or "",
                    singularity_command=singularity_command,
                    error_msg=lines,
                )

        # Copy cached download if we are using the cache
        if cache_path:
            log.debug(f"Copying {container} from cache: '{os.path.basename(out_path)}'")
            progress.update(task, current_log="Copying from cache to target directory")
            shutil.copyfile(cache_path, out_path)

        # Create symlinks to ensure that the images are found even with different registries being used.
        self.symlink_singularity_images(output_path)

        progress.remove_task(task)

    def compress_download(self) -> None:
        """Take the downloaded files and make a compressed .tar.gz archive."""
        log.debug(f"Creating archive: {self.output_filename}")

        # .tar.gz and .tar.bz2 files
        if self.compress_type in ["tar.gz", "tar.bz2"]:
            ctype = self.compress_type.split(".")[1]
            with tarfile.open(self.output_filename, f"w:{ctype}") as tar:
                tar.add(self.outdir, arcname=os.path.basename(self.outdir))
            tar_flags = "xzf" if ctype == "gz" else "xjf"
            log.info(f"Command to extract files: [bright_magenta]tar -{tar_flags} {self.output_filename}[/]")

        # .zip files
        if self.compress_type == "zip":
            with ZipFile(self.output_filename, "w") as zip_file:
                # Iterate over all the files in directory
                for folder_name, _, filenames in os.walk(self.outdir):
                    for filename in filenames:
                        # create complete filepath of file in directory
                        file_path = os.path.join(folder_name, filename)
                        # Add file to zip
                        zip_file.write(file_path)
            log.info(f"Command to extract files: [bright_magenta]unzip {self.output_filename}[/]")

        # Delete original files
        log.debug(f"Deleting uncompressed files: '{self.outdir}'")
        shutil.rmtree(self.outdir)

        # Calculate md5sum for output file
        log.info(f"MD5 checksum for '{self.output_filename}': [blue]{nf_core.utils.file_md5(self.output_filename)}[/]")


class WorkflowRepo(SyncedRepo):
    """
    An object to store details about a locally cached workflow repository.

    Important Attributes:
        fullname: The full name of the repository, ``nf-core/{self.pipelinename}``.
        local_repo_dir (str): The local directory, where the workflow is cloned into. Defaults to ``$HOME/.cache/nf-core/nf-core/{self.pipeline}``.

    """

    def __init__(
        self,
        remote_url,
        revision,
        commit,
        additional_tags,
        location=None,
        hide_progress=False,
        in_cache=True,
    ):
        """
        Initializes the object and clones the workflows git repository if it is not already present

        Args:
            remote_url (str): The URL of the remote repository. Defaults to None.
            self.revision (list of str): The revisions to include. A list of strings.
            commits (dict of str): The checksums to linked with the revisions.
            no_pull (bool, optional): Whether to skip the pull step. Defaults to False.
            hide_progress (bool, optional): Whether to hide the progress bar. Defaults to False.
            in_cache (bool, optional): Whether to clone the repository from the cache. Defaults to False.
        """
        self.remote_url = remote_url
        if isinstance(revision, str):
            self.revision = [revision]
        elif isinstance(revision, list):
            self.revision = [*revision]
        else:
            self.revision = []
        if isinstance(commit, str):
            self.commit = [commit]
        elif isinstance(commit, list):
            self.commit = [*commit]
        else:
            self.commit = []
        self.fullname = nf_core.modules.modules_utils.repo_full_name_from_remote(self.remote_url)
        self.retries = 0  # retries for setting up the locally cached repository
        self.hide_progress = hide_progress

        self.setup_local_repo(remote=remote_url, location=location, in_cache=in_cache)

        # additional tags to be added to the repository
        self.additional_tags = additional_tags if additional_tags else None

    def __repr__(self):
        """Called by print, creates representation of object"""
        return f"<Locally cached repository: {self.fullname}, revisions {', '.join(self.revision)}\n cached at: {self.local_repo_dir}>"

    @property
    def heads(self):
        return self.repo.heads

    @property
    def tags(self):
        return self.repo.tags

    def access(self):
        if os.path.exists(self.local_repo_dir):
            return self.local_repo_dir
        else:
            return None

    def checkout(self, commit):
        return super().checkout(commit)

    def get_remote_branches(self, remote_url):
        return super().get_remote_branches(remote_url)

    def retry_setup_local_repo(self, skip_confirm=False):
        self.retries += 1
        if skip_confirm or rich.prompt.Confirm.ask(
            f"[violet]Delete local cache '{self.local_repo_dir}' and try again?"
        ):
            if (
                self.retries > 1
            ):  # One unconfirmed retry is acceptable, but prevent infinite loops without user interaction.
                raise DownloadError(
                    f"Errors with locally cached repository of '{self.fullname}'. Please delete '{self.local_repo_dir}' manually and try again."
                )
            if not skip_confirm:  # Feedback to user for manual confirmation.
                log.info(f"Removing '{self.local_repo_dir}'")
            shutil.rmtree(self.local_repo_dir)
            self.setup_local_repo(self.remote_url, in_cache=False)
        else:
            raise DownloadError("Exiting due to error with locally cached Git repository.")

    def setup_local_repo(self, remote, location=None, in_cache=True):
        """
        Sets up the local git repository. If the repository has been cloned previously, it
        returns a git.Repo object of that clone. Otherwise it tries to clone the repository from
        the provided remote URL and returns a git.Repo of the new clone.

        Args:
            remote (str): git url of remote
            location (Path): location where the clone should be created/cached.
            in_cache (bool, optional): Whether to clone the repository from the cache. Defaults to False.
        Sets self.repo
        """
        if location:
            self.local_repo_dir = os.path.join(location, self.fullname)
        else:
            self.local_repo_dir = os.path.join(NFCORE_DIR if not in_cache else NFCORE_CACHE_DIR, self.fullname)

        try:
            if not os.path.exists(self.local_repo_dir):
                try:
                    pbar = rich.progress.Progress(
                        "[bold blue]{task.description}",
                        rich.progress.BarColumn(bar_width=None),
                        "[bold yellow]{task.fields[state]}",
                        transient=True,
                        disable=os.environ.get("HIDE_PROGRESS", None) is not None or self.hide_progress,
                    )
                    with pbar:
                        self.repo = git.Repo.clone_from(
                            remote,
                            self.local_repo_dir,
                            progress=RemoteProgressbar(pbar, self.fullname, self.remote_url, "Cloning"),
                        )
                    super().update_local_repo_status(self.fullname, True)
                except GitCommandError:
                    raise DownloadError(f"Failed to clone from the remote: `{remote}`")
            else:
                self.repo = git.Repo(self.local_repo_dir)

                if super().no_pull_global:
                    super().update_local_repo_status(self.fullname, True)
                # If the repo is already cloned, fetch the latest changes from the remote
                if not super().local_repo_synced(self.fullname):
                    pbar = rich.progress.Progress(
                        "[bold blue]{task.description}",
                        rich.progress.BarColumn(bar_width=None),
                        "[bold yellow]{task.fields[state]}",
                        transient=True,
                        disable=os.environ.get("HIDE_PROGRESS", None) is not None or self.hide_progress,
                    )
                    with pbar:
                        self.repo.remotes.origin.fetch(
                            progress=RemoteProgressbar(pbar, self.fullname, self.remote_url, "Pulling")
                        )
                    super().update_local_repo_status(self.fullname, True)

        except (GitCommandError, InvalidGitRepositoryError) as e:
            log.error(f"[red]Could not set up local cache of modules repository:[/]\n{e}\n")
            self.retry_setup_local_repo()

    def tidy_tags_and_branches(self):
        """
        Function to delete all tags and branches that are not of interest to the downloader.
        This allows a clutter-free experience in Seqera Platform. The untagged commits are evidently still available.

        However, due to local caching, the downloader might also want access to revisions that had been deleted before.
        In that case, don't bother with re-adding the tags and rather download  anew from Github.
        """
        if self.revision and self.repo and self.repo.tags:
            # create a set to keep track of the revisions to process & check
            desired_revisions = set(self.revision)

            # determine what needs pruning
            tags_to_remove = {tag for tag in self.repo.tags if tag.name not in desired_revisions.union({"latest"})}
            heads_to_remove = {head for head in self.repo.heads if head.name not in desired_revisions.union({"latest"})}

            try:
                # delete unwanted tags from repository
                for tag in tags_to_remove:
                    self.repo.delete_tag(tag)

                # switch to a revision that should be kept, because deleting heads fails, if they are checked out (e.g. "master")
                self.checkout(self.revision[0])

                # delete unwanted heads/branches from repository
                for head in heads_to_remove:
                    self.repo.delete_head(head)

                # ensure all desired revisions/branches are available
                for revision in desired_revisions:
                    if not self.repo.is_valid_object(revision):
                        self.checkout(revision)
                        self.repo.create_head(revision, revision)
                        if self.repo.head.is_detached:
                            self.repo.head.reset(index=True, working_tree=True)

                # no branch exists, but one is required for Seqera Platform's UI to display revisions correctly). Thus, "latest" will be created.
                if not bool(self.repo.heads):
                    if self.repo.is_valid_object("latest"):
                        # "latest" exists as tag but not as branch
                        self.repo.create_head("latest", "latest")  # create a new head for latest
                        self.checkout("latest")
                    else:
                        # desired revisions may contain arbitrary branch names that do not correspond to valid sematic versioning patterns.
                        valid_versions = [
                            version_parser(v)
                            for v in desired_revisions
                            if re.match(r"\d+\.\d+(?:\.\d+)*(?:[\w\-_])*", v)
                        ]
                        # valid versions sorted in ascending order, last will be aliased as "latest".
                        latest = sorted(valid_versions)[-1]
                        self.repo.create_head("latest", latest)
                        self.checkout(latest)
                    if self.repo.head.is_detached:
                        self.repo.head.reset(index=True, working_tree=True)

                # Apply the custom additional tags to the repository
                self.__add_additional_tags()

                # get all tags and available remote_branches
                completed_revisions = {revision.name for revision in self.repo.heads + self.repo.tags}

                # verify that all requested revisions are available.
                # a local cache might lack revisions that were deleted during a less comprehensive previous download.
                if bool(desired_revisions - completed_revisions):
                    log.info(
                        f"Locally cached version of the pipeline lacks selected revisions {', '.join(desired_revisions - completed_revisions)}. Downloading anew from GitHub..."
                    )
                    self.retry_setup_local_repo(skip_confirm=True)
                    self.tidy_tags_and_branches()
            except (GitCommandError, InvalidGitRepositoryError) as e:
                log.error(f"[red]Adapting your pipeline download unfortunately failed:[/]\n{e}\n")
                self.retry_setup_local_repo(skip_confirm=True)
                raise DownloadError(e) from e

    # "Private" method to add the additional custom tags to the repository.
    def __add_additional_tags(self) -> None:
        if self.additional_tags:
            # example.com is reserved by the Internet Assigned Numbers Authority (IANA)  as special-use domain names for documentation purposes.
            # Although "dev-null" is a syntactically-valid local-part that is equally valid for delivery,
            # and only the receiving MTA can decide whether to accept it, it is to my best knowledge configured with
            # a Postfix discard mail delivery agent (https://www.postfix.org/discard.8.html), so incoming mails should be sinkholed.
            self.ensure_git_user_config(f"nf-core download v{nf_core.__version__}", "dev-null@example.com")

            for additional_tag in self.additional_tags:
                # A valid git branch or tag name can contain alphanumeric characters, underscores, hyphens, and dots.
                # But it must not start with a dot, hyphen or underscore and also cannot contain two consecutive dots.
                if re.match(r"^\w[\w_.-]+={1}\w[\w_.-]+$", additional_tag) and ".." not in additional_tag:
                    anchor, tag = additional_tag.split("=")
                    if self.repo.is_valid_object(anchor) and not self.repo.is_valid_object(tag):
                        try:
                            self.repo.create_tag(
                                tag, ref=anchor, message=f"Synonynmous tag to {anchor}; added by `nf-core download`."
                            )
                        except (GitCommandError, InvalidGitRepositoryError) as e:
                            log.error(f"[red]Additional tag(s) could not be applied:[/]\n{e}\n")
                    else:
                        if not self.repo.is_valid_object(anchor):
                            log.error(
                                f"[red]Adding tag '{tag}' to '{anchor}' failed.[/]\n Mind that '{anchor}' must be a valid git reference that resolves to a commit."
                            )
                        if self.repo.is_valid_object(tag):
                            log.error(
                                f"[red]Adding tag '{tag}' to '{anchor}' failed.[/]\n Mind that '{tag}' must not exist hitherto."
                            )
                else:
                    log.error(f"[red]Could not apply invalid `--tag` specification[/]: '{additional_tag}'")

    def bare_clone(self, destination):
        if self.repo:
            try:
                destfolder = os.path.abspath(destination)
                if not os.path.exists(destfolder):
                    os.makedirs(destfolder)
                if os.path.exists(destination):
                    shutil.rmtree(os.path.abspath(destination))
                self.repo.clone(os.path.abspath(destination), bare=True)
            except (OSError, GitCommandError, InvalidGitRepositoryError) as e:
                log.error(f"[red]Failure to create the pipeline download[/]\n{e}\n")


# Distinct errors for the container download, required for acting on the exceptions


class ContainerError(Exception):
    """A class of errors related to pulling containers with Singularity/Apptainer"""

    def __init__(
        self,
        container,
        registry,
        address,
        absolute_URI,
        out_path,
        singularity_command,
        error_msg,
    ):
        self.container = container
        self.registry = registry
        self.address = address
        self.absolute_URI = absolute_URI
        self.out_path = out_path
        self.singularity_command = singularity_command
        self.error_msg = error_msg

        for line in error_msg:
            if re.search(r"dial\stcp.*no\ssuch\shost", line):
                self.error_type = self.RegistryNotFoundError(self)
                break
            elif (
                re.search(r"requested\saccess\sto\sthe\sresource\sis\sdenied", line)
                or re.search(r"StatusCode:\s404", line)
                or re.search(r"400|Bad\s?Request", line)
                or re.search(r"invalid\sstatus\scode\sfrom\sregistry\s400", line)
            ):
                # Unfortunately, every registry seems to return an individual error here:
                # Docker.io: denied: requested access to the resource is denied
                #                    unauthorized: authentication required
                # Quay.io: StatusCode: 404,  <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n']
                # ghcr.io: Requesting bearer token: invalid status code from registry 400 (Bad Request)
                self.error_type = self.ImageNotFoundError(self)
                break
            elif re.search(r"manifest\sunknown", line):
                self.error_type = self.InvalidTagError(self)
                break
            elif re.search(r"Image\sfile\salready\sexists", line):
                self.error_type = self.ImageExistsError(self)
                break
            else:
                continue
        else:
            self.error_type = self.OtherError(self)

        log.error(self.error_type.message)
        log.info(self.error_type.helpmessage)
        log.debug(f'Failed command:\n{" ".join(singularity_command)}')
        log.debug(f'Singularity error messages:\n{"".join(error_msg)}')

        raise self.error_type

    class RegistryNotFoundError(ConnectionRefusedError):
        """The specified registry does not resolve to a valid IP address"""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = (
                f'[bold red]The specified container library "{self.error_log.registry}" is invalid or unreachable.[/]\n'
            )
            self.helpmessage = (
                f'Please check, if you made a typo when providing "-l / --library {self.error_log.registry}"\n'
            )
            super().__init__(self.message, self.helpmessage, self.error_log)

    class ImageNotFoundError(FileNotFoundError):
        """The image can not be found in the registry"""

        def __init__(self, error_log):
            self.error_log = error_log
            if not self.error_log.absolute_URI:
                self.message = (
                    f'[bold red]"Pulling "{self.error_log.container}" from "{self.error_log.address}" failed.[/]\n'
                )
                self.helpmessage = f'Saving image of "{self.error_log.container}" failed.\nPlease troubleshoot the command \n"{" ".join(self.error_log.singularity_command)}" manually.f\n'
            else:
                self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
                self.helpmessage = f'Please try to rerun \n"{" ".join(self.error_log.singularity_command)}" manually with a different registry.f\n'

            super().__init__(self.message)

    class InvalidTagError(AttributeError):
        """Image and registry are valid, but the (version) tag is not"""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = f'[bold red]"{self.error_log.address.split(":")[-1]}" is not a valid tag of "{self.error_log.container}"[/]\n'
            self.helpmessage = f'Please chose a different library than {self.error_log.registry}\nor try to locate the "{self.error_log.address.split(":")[-1]}" version of "{self.error_log.container}" manually.\nPlease troubleshoot the command \n"{" ".join(self.error_log.singularity_command)}" manually.\n'
            super().__init__(self.message)

    class ImageExistsError(FileExistsError):
        """Image already exists in cache/output directory."""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = (
                f'[bold red]"{self.error_log.container}" already exists at destination and cannot be pulled[/]\n'
            )
            self.helpmessage = f'Saving image of "{self.error_log.container}" failed, because "{self.error_log.out_path}" exists.\nPlease troubleshoot the command \n"{" ".join(self.error_log.singularity_command)}" manually.\n'
            super().__init__(self.message)

    class OtherError(RuntimeError):
        """Undefined error with the container"""

        def __init__(self, error_log):
            self.error_log = error_log
            if not self.error_log.absolute_URI:
                self.message = f'[bold red]"{self.error_log.container}" failed for unclear reasons.[/]\n'
                self.helpmessage = f'Pulling of "{self.error_log.container}" failed.\nPlease troubleshoot the command \n"{" ".join(self.error_log.singularity_command)}" manually.\n'
            else:
                self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
                self.helpmessage = f'Please try to rerun \n"{" ".join(self.error_log.singularity_command)}" manually with a different registry.f\n'

            super().__init__(self.message, self.helpmessage, self.error_log)
