"""Downloads a nf-core pipeline to the local file system."""

import io
import json
import logging
import os
import re
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zipfile import ZipFile

import questionary
import requests
import rich
import rich.progress

import nf_core
import nf_core.modules.modules_utils
import nf_core.pipelines.download.utils
import nf_core.pipelines.list
import nf_core.utils
from nf_core.pipelines.download.container_fetcher import ContainerFetcher
from nf_core.pipelines.download.docker import DockerFetcher
from nf_core.pipelines.download.singularity import SingularityFetcher
from nf_core.pipelines.download.utils import (
    NF_INSPECT_MIN_NF_VERSION,
    DownloadError,
    prioritize_direct_download,
    rectify_raw_container_matches,
)
from nf_core.pipelines.download.workflow_repo import WorkflowRepo
from nf_core.utils import (
    SingularityCacheFilePathValidator,
    run_cmd,
)

log = logging.getLogger(__name__)
stderr = rich.console.Console(
    stderr=True,
    style="dim",
    highlight=False,
    force_terminal=nf_core.utils.rich_force_colors(),
)


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
        parallel (int): The number of parallel downloads to use. Defaults to 4.
    """

    def __init__(
        self,
        pipeline: Optional[str] = None,
        revision: Optional[str] = None,
        outdir=None,
        compress_type: Optional[str] = None,
        force: bool = False,
        platform: bool = False,
        download_configuration=None,
        additional_tags: Optional[list[str] | str] = None,
        container_system=None,
        container_library=None,
        container_cache_utilisation=None,
        container_cache_index=None,
        parallel: int = 4,
        hide_progress: bool = False,
    ):
        # Verify that the flags provided make sense together
        if (
            container_system == "docker"
            and container_cache_utilisation != "copy"
            and container_cache_utilisation is not None
        ):
            raise DownloadError(
                "Only the 'copy' option for --container-cache-utilisation is supported for Docker images. "
            )

        self.pipeline = pipeline
        if isinstance(revision, str):
            self.revision = [revision]
        elif isinstance(revision, tuple):
            self.revision = [*revision]
        else:
            self.revision = []
        self.outdir = Path(outdir) if outdir is not None else None
        self.output_filename: Optional[Path] = None
        self.compress_type = compress_type
        self.force = force
        self.hide_progress = hide_progress
        self.platform = platform
        self.fullname: Optional[str] = None
        # downloading configs is not supported for Seqera Platform downloads.
        self.include_configs = True if download_configuration == "yes" and not bool(platform) else False
        # Additional tags to add to the downloaded pipeline. This enables to mark particular commits or revisions with
        # additional tags, e.g. "stable", "testing", "validated", "production" etc. Since this requires a git-repo, it is only
        # available for the bare / Seqera Platform download.
        self.additional_tags: Optional[list[str]]
        if isinstance(additional_tags, str) and bool(len(additional_tags)) and self.platform:
            self.additional_tags = [additional_tags]
        elif isinstance(additional_tags, tuple) and bool(len(additional_tags)) and self.platform:
            self.additional_tags = [*additional_tags]
        else:
            self.additional_tags = None

        self.container_system = container_system
        # Check if a cache or libraries were specfied even though singularity was not
        if container_cache_index and self.container_system != "singularity":
            log.warning("The flag '--container-cache-index' is set, but not selected to fetch singularity images")
            self.prompt_use_singularity(
                "The '--container-cache-index' flag is only applicable when fetching singularity images"
            )

        if container_library and self.container_system != "singularity":
            log.warning("You have specified container libraries but not selected to fetch singularity image")
            self.prompt_use_singularity(
                "The '--container-library' flag is only applicable when fetching singularity images"
            )  # Is this correct?

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
        self.parallel = parallel

        self.wf_revisions: list[dict[str, Any]] = []
        self.wf_branches: dict[str, Any] = {}
        self.wf_sha: dict[str, str] = {}
        self.wf_download_url: dict[str, str] = {}
        self.nf_config: dict[str, str] = {}
        self.containers: list[str] = []
        self.containers_remote: list[str] = []  # stores the remote images provided in the file.

        # Fetch remote workflows
        self.wfs = nf_core.pipelines.list.Workflows()
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
            # Prompt the user for whether containers should be downloaded
            if self.container_system is None:
                self.prompt_container_download()

            log.warning(self.container_system)
            # Check if we need to set up a cache directory for Singularity
            if self.container_system == "singularity":
                # Check if the env variable for the Singularity cache directory is set
                if os.environ.get("NXF_SINGULARITY_CACHEDIR") is None and stderr.is_interactive:
                    # Prompt for the Singularity cache directory
                    self.prompt_singularity_cachedir_creation()

                    if self.container_cache_utilisation is None:
                        # No choice regarding singularity cache has been made.
                        self.prompt_singularity_cachedir_utilization()

                if self.container_cache_utilisation == "remote":
                    # If we have a remote cache, we need to read it
                    if self.container_cache_index is None and stderr.is_interactive:
                        self.prompt_singularity_cachedir_remote()
                    # If we have remote containers, we need to read them
                    if self.container_cache_utilisation == "remote" and self.container_cache_index is not None:
                        self.read_remote_containers()
                    else:
                        log.warning("[red]No remote cache index specified, skipping remote container download.[/]")

            # Nothing meaningful to compress here.
            if not self.platform:
                self.prompt_compression_type()
        except AssertionError as e:
            raise DownloadError(e) from e

        summary_log = [
            f"Pipeline revision: '{', '.join(self.revision) if len(self.revision) < 5 else self.revision[0] + ',[' + str(len(self.revision) - 2) + ' more revisions],' + self.revision[-1]}'",
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
            self.output_filename = self.outdir.with_suffix(".git")
            summary_log.append(f"Output file: '{self.output_filename}'")
        elif self.compress_type is not None:
            self.output_filename = self.outdir.with_suffix(self.compress_type)
            summary_log.append(f"Output file: '{self.output_filename}'")
        else:
            summary_log.append(f"Output directory: '{self.outdir}'")

        if not self.platform:
            # Only show entry, if option was prompted.
            summary_log.append(f"Include default institutional configuration: '{self.include_configs}'")
        else:
            summary_log.append(f"Enabled for Seqera Platform: '{self.platform}'")

        # Check that the outdir doesn't already exist
        if self.outdir is not None and self.outdir.exists():
            if not self.force:
                raise DownloadError(
                    f"Output directory '{self.outdir}' already exists (use [red]--force[/] to overwrite)"
                )
            log.warning(f"Deleting existing output directory: '{self.outdir}'")
            shutil.rmtree(self.outdir)

        # Check that compressed output file doesn't already exist
        if self.output_filename and self.output_filename.exists():
            if not self.force:
                raise DownloadError(
                    f"Output file '{self.output_filename}' already exists (use [red]--force[/] to overwrite)"
                )
            log.warning(f"Deleting existing output file: '{self.output_filename}'")
            self.output_filename.unlink()

        # Summary log
        indent = 2
        sep = "\n" + " " * indent
        log_lines = sep.join(summary_log)
        log.info(f"Saving '{self.pipeline}'{sep}{log_lines}")

        # Perform the actual download
        if self.platform:
            log.info("Downloading workflow for Seqera Platform")
            self.download_workflow_platform()
        else:
            log.info("Downloading workflow for static")
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
            if self.container_system in {"singularity", "docker"}:
                self.find_container_images(self.outdir / revision_dirname)
                self.gather_registries(self.outdir / revision_dirname)

                try:
                    self.download_container_images(current_revision=item[0])
                except OSError as e:
                    raise DownloadError(f"[red]{e}[/]") from e

        # Compress into an archive
        if self.compress_type is not None:
            log.info("Compressing output into archive")
            self.compress_download()

        # If docker is the selected image format, then we should tell the
        # user how to load the images into the offline daemon
        if self.container_system == "docker":
            self.write_docker_load_message()

    def download_workflow_platform(self, location: Optional[Path] = None):
        """Create a bare-cloned git repository of the workflow, so it can be launched with `tw launch` as file:/ pipeline"""
        assert self.outdir is not None  # mypy
        assert self.output_filename is not None  # mypy

        log.info("Collecting workflow from GitHub")

        self.workflow_repo = WorkflowRepo(
            remote_url=f"https://github.com/{self.pipeline}.git",
            revision=self.revision if self.revision else None,
            commit=self.wf_sha.values() if bool(self.wf_sha) else None,
            additional_tags=self.additional_tags,
            location=location if location else None,  # manual location is required for the tests to work
            in_cache=False,
        )

        # Remove tags for those revisions that had not been selected
        self.workflow_repo.tidy_tags_and_branches()

        # create a bare clone of the modified repository needed for Seqera Platform
        self.workflow_repo.bare_clone(self.outdir / self.output_filename)

        # extract the required containers
        if self.container_system in {"singularity", "docker"}:
            for revision, commit in self.wf_sha.items():
                # Checkout the repo in the current revision
                self.workflow_repo.checkout(commit)
                # Collect all required singularity images
                self.find_container_images(self.workflow_repo.access())
                self.gather_registries(self.workflow_repo.access())

                try:
                    self.download_container_images(current_revision=revision)
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

    def prompt_revision(self) -> None:
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
        """Find specified revision / branch / commit hash"""

        for revision in self.revision:  # revision is a list of strings, but may be of length 1
            # Branch
            if revision in self.wf_branches.keys():
                self.wf_sha = {**self.wf_sha, revision: self.wf_branches[revision]}

            else:
                # Revision
                for r in self.wf_revisions:
                    if r["tag_name"] == revision:
                        self.wf_sha = {**self.wf_sha, revision: r["tag_sha"]}
                        break

                else:
                    # Commit - full or short hash
                    if commit_id := nf_core.utils.get_repo_commit(self.pipeline, revision):
                        self.wf_sha = {**self.wf_sha, revision: commit_id}
                        continue

                    # Can't find the revisions or branch - throw an error
                    log.info(
                        "Available {} revisions: '{}'".format(
                            self.pipeline,
                            "', '".join([r["tag_name"] for r in self.wf_revisions]),
                        )
                    )
                    log.info("Available {} branches: '{}'".format(self.pipeline, "', '".join(self.wf_branches.keys())))
                    raise AssertionError(
                        f"Not able to find revision / branch / commit '{revision}' for {self.pipeline}"
                    )

        # Set the outdir
        if not self.outdir:
            if len(self.wf_sha) > 1:
                self.outdir = Path(
                    f"{self.pipeline.replace('/', '-').lower()}_{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
                )
            else:
                self.outdir = Path(f"{self.pipeline.replace('/', '-').lower()}_{self.revision[0]}")

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
                choices=["none", "singularity", "docker"],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

    def prompt_singularity_cachedir_creation(self):
        """Prompt about using $NXF_SINGULARITY_CACHEDIR if not already set"""
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
                if prompt_cachedir_path == "":
                    log.error("Not using [blue]$NXF_SINGULARITY_CACHEDIR[/]")
                    break
                cachedir_path = Path(prompt_cachedir_path).expanduser().absolute()
                if not cachedir_path.is_dir():
                    log.error(f"'{cachedir_path}' is not a directory.")
                    cachedir_path = None
            if cachedir_path:
                os.environ["NXF_SINGULARITY_CACHEDIR"] = str(cachedir_path)

                """
                Optionally, create a permanent entry for the NXF_SINGULARITY_CACHEDIR in the terminal profile.
                Currently support for bash and zsh.
                ToDo: "sh", "dash", "ash","csh", "tcsh", "ksh", "fish", "cmd", "powershell", "pwsh"?
                """

                if os.getenv("SHELL", "") == "/bin/bash":
                    shellprofile_path = Path("~/~/.bash_profile").expanduser()
                    if not shellprofile_path.is_file():
                        shellprofile_path = Path("~/.bashrc").expanduser()
                        if not shellprofile_path.is_file():
                            shellprofile_path = None
                elif os.getenv("SHELL", "") == "/bin/zsh":
                    shellprofile_path = Path("~/.zprofile").expanduser()
                    if not shellprofile_path.is_file():
                        shellprofile_path = Path("~/.zshenv").expanduser()
                        if not shellprofile_path.is_file():
                            shellprofile_path = None
                else:
                    shellprofile_path = Path("~/.profile").expanduser()
                    if not shellprofile_path.is_file():
                        shellprofile_path = None

                if shellprofile_path is not None:
                    stderr.print(
                        f"\nSo that [blue]$NXF_SINGULARITY_CACHEDIR[/] is always defined, you can add it to your [blue not bold]~/{shellprofile_path.name}[/] file ."
                        "This will then be automatically set every time you open a new terminal. We can add the following line to this file for you: \n"
                        f'[blue]export NXF_SINGULARITY_CACHEDIR="{cachedir_path}"[/]'
                    )
                    append_to_file = rich.prompt.Confirm.ask(
                        f"[blue bold]?[/] [bold]Add to [blue not bold]~/{shellprofile_path.name}[/] ?[/]"
                    )
                    if append_to_file:
                        with open(shellprofile_path.expanduser(), "a") as f:
                            f.write(
                                "\n\n#######################################\n"
                                f"## Added by `nf-core pipelines download` v{nf_core.__version__} ##\n"
                                + f'export NXF_SINGULARITY_CACHEDIR="{cachedir_path}"'
                                + "\n#######################################\n"
                            )
                        log.info(f"Successfully wrote to [blue]{shellprofile_path}[/]")
                        log.warning(
                            "You will need reload your terminal after the download completes for this to take effect."
                        )

    def prompt_singularity_cachedir_utilization(self):
        """Ask if we should *only* use $NXF_SINGULARITY_CACHEDIR without copying into target"""
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
        # Prompt user for a file listing the contents of the remote cache directory
        cachedir_index = None
        while cachedir_index is None:
            prompt_cachedir_index = questionary.path(
                "Specify a list of the container images that are already present on the remote system:",
                validate=SingularityCacheFilePathValidator,
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
            if prompt_cachedir_index == "":
                log.error("Will disregard contents of a remote [blue]$NXF_SINGULARITY_CACHEDIR[/]")
                self.container_cache_index = None
                self.container_cache_utilisation = "copy"
                break
            cachedir_index = Path(prompt_cachedir_index).expanduser().absolute()
            if not os.access(cachedir_index, os.R_OK):
                log.error(f"'{cachedir_index}' is not a readable file.")
                cachedir_index = None
        if cachedir_index:
            self.container_cache_index = cachedir_index

    def read_remote_containers(self):
        """Reads the file specified as index for the remote Singularity cache dir"""
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
                log.debug(self.containers_remote)
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

    def prompt_use_singularity(self, fail_message) -> None:
        use_singularity = questionary.confirm(
            "Do you want to download singularity images?",
            style=nf_core.utils.nfcore_question_style,
        ).ask()
        if use_singularity:
            self.container_system = "singularity"
        else:
            raise DownloadError(fail_message)

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
        # account for name collisions, if there is a branch / release named "configs" or container output dir
        if revision_dirname in ["configs", self.get_container_output_dir()]:
            revision_dirname = re.sub("[^0-9a-zA-Z]+", "_", self.pipeline + revision_dirname)

        # Rename the internal directory name to be more friendly
        gh_name = f"{self.pipeline}-{wf_sha if bool(wf_sha) else ''}".split("/")[-1]
        ((self.outdir / gh_name).rename(self.outdir / revision_dirname),)

        # Make downloaded files executable
        for dirpath, _, filelist in (self.outdir / revision_dirname).walk():
            for fname in filelist:
                (dirpath / fname).chmod(0o775)

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
        (self.outdir / configs_local_dir).rename(self.outdir / "configs")

        # Make downloaded files executable

        for dirpath, _, filelist in (self.outdir / "configs").walk():
            for fname in filelist:
                (dirpath / fname).chmod(0o775)

    def wf_use_local_configs(self, revision_dirname: str):
        """Edit the downloaded nextflow.config file to use the local config files"""

        assert self.outdir is not None  # mypy
        nfconfig_fn = (self.outdir / revision_dirname) / "nextflow.config"
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
                f"\n\n// Added by `nf-core pipelines download` v{nf_core.__version__} //\n"
                + 'singularity.cacheDir = "${projectDir}/../singularity-images/"'
                + "\n///////////////////////////////////////"
            )

        # Write the file out again
        log.debug(f"Updating '{nfconfig_fn}'")
        with open(nfconfig_fn, "w") as nfconfig_fh:
            nfconfig_fh.write(nfconfig)

    def write_docker_load_message(self):
        # There is not direct Nextflow support for loading docker images like we do for singularity above
        # Instead we give the user a `bash` command to load the downloaded docker images into the offline docker daemon
        # Courtesy of @vmkalbskopf in https://github.com/nextflow-io/nextflow/discussions/4708
        docker_load_command = "ls -1 *.tar | xargs --no-run-if-empty -L 1 docker load -i"
        indent_spaces = 4
        docker_img_dir = self.get_container_output_dir()
        stderr.print(
            "\n"
            + (1 * indent_spaces * " " + f"Downloaded docker images written to [blue not bold]'{docker_img_dir}'[/]. ")
            + (0 * indent_spaces * " " + "After copying the pipeline and images to the offline machine, run\n\n")
            + (2 * indent_spaces * " " + f"[blue bold]{docker_load_command}[/]\n\n")
            + (
                1 * indent_spaces * " "
                + f"inside [blue not bold]'{docker_img_dir}'[/] to load the images into the offline docker daemon."
            )
            + "\n"
        )

    def find_container_images(self, workflow_directory: Path) -> None:
        """Find container image names for workflow using the `nextflow inspect` command.

        ONLY WORKS FOR NEXTFLOW >= 25.04.4

        Falls back to using `find_container_images_legacy()` when `nextflow inspect` fails.
        """
        # Check if we have an outdated Nextflow version
        if not nf_core.pipelines.download.utils.check_nextflow_version(NF_INSPECT_MIN_NF_VERSION):
            log.warning(
                "The `nextflow inspect` command requires Nextflow version >= "
                + nf_core.pipelines.download.utils.pretty_nf_version(NF_INSPECT_MIN_NF_VERSION)
            )
            log.info("Falling back to legacy container extraction method.")
            self.find_container_images_legacy(workflow_directory)
        else:
            log.info(
                "Fetching container names for workflow using [blue bold]nextflow inspect[/]. This might take a while."
            )
            try:
                self.find_container_images_nf_inspect(workflow_directory)
                return

            except RuntimeError as e:
                log.warning("Running 'nextflow inspect' failed with the following error")
                log.warning(e)

            except KeyError as e:
                log.warning("Failed to parse output of 'nextflow inspect' to extract containers")
                log.debug(e)

            self.find_container_images_legacy(workflow_directory)

    def find_container_images_nf_inspect(self, workflow_directory: Path, entrypoint="main.nf"):
        # TODO: Select container system via profile. Is this stable enough?
        # NOTE: We will likely don't need this after the switch to Seqera containers
        profile = f"-profile {self.container_system}" if self.container_system else ""

        # Run nextflow inspect
        executable = "nextflow"
        cmd_params = f"inspect -format json {profile} {workflow_directory / entrypoint}"
        cmd_out = run_cmd(executable, cmd_params)
        if cmd_out is None:
            raise RuntimeError("Failed to run `nextflow inspect`. Please check your Nextflow installation.")

        out, _ = cmd_out
        out_json = json.loads(out)
        # NOTE: We only save the container strings to comply with the legacy function.
        named_containers = {proc["name"]: proc["container"] for proc in out_json["processes"]}

        self.containers = list(set(named_containers.values()))

    def find_container_images_legacy(self, workflow_directory: Path) -> None:
        """Find container image names for workflow.

        DEPRECATION NOTE: USED FOR NEXTFLOW VERSIONS < 25.04.4

        Starts by using `nextflow config` to pull out any process.container
        declarations. This works for DSL1. It should return a simple string with resolved logic,
        but not always, e.g. not for differentialabundance 1.2.0

        Second, we look for DSL2 containers. These can't be found with
        `nextflow config` at the time of writing, so we scrape the pipeline files.
        This returns raw matches that will likely need to be cleaned.
        """

        log.warning("Using legacy container extraction method. This will be deprecated in the future.")
        log.debug("Fetching container names for workflow ")
        # since this is run for multiple revisions now, account for previously detected containers.
        previous_findings = [] if not self.containers else self.containers
        config_findings = []
        module_findings = []

        # Use linting code to parse the pipeline nextflow config
        self.nf_config = nf_core.utils.fetch_wf_config(Path(workflow_directory))

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
                    config_findings.append((k, v.strip("'\""), self.nf_config, "Nextflow configs"))

        # rectify the container paths found in the config
        # Raw config_findings may yield multiple containers, so better create a shallow copy of the list, since length of input and output may be different ?!?
        config_findings = rectify_raw_container_matches(config_findings[:])

        # Recursive search through any DSL2 module files for container spec lines.
        for subdir, _, files in (workflow_directory / "modules").walk():
            for file in files:
                if file.endswith(".nf"):
                    file_path = subdir / file
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
        module_findings = rectify_raw_container_matches(module_findings[:])

        # Again clean list, in case config declares Docker URI but module or previous finding already had the http:// download
        self.containers = prioritize_direct_download(previous_findings + config_findings + module_findings)

    def gather_registries(self, workflow_directory: str) -> None:
        """Fetch the registries from the pipeline config and CLI arguments and store them in a set.
        This is needed to symlink downloaded container images so Nextflow will find them.
        """

        # should exist, because find_container_images() is always called before
        if not self.nf_config:
            self.nf_config = nf_core.utils.fetch_wf_config(Path(workflow_directory))

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
        self.registry_set.add("depot.galaxyproject.org/singularity")

        # add community.wave.seqera.io/library to the set to support the new Seqera Docker container registry
        self.registry_set.add("community.wave.seqera.io/library")

        # add chttps://community-cr-prod.seqera.io/docker/registry/v2/ to the set to support the new Seqera Singularity container registry
        self.registry_set.add("community-cr-prod.seqera.io/docker/registry/v2")

    def get_container_output_dir(self) -> Path:
        assert self.outdir is not None  # mypy
        return self.outdir / f"{self.container_system}-images"

    def download_container_images(self, current_revision: str = "") -> None:
        """Loop through container names and download Singularity images"""

        if len(self.containers) == 0:
            log.info("No container names found in workflow")
        else:
            log.info(
                f"Processing workflow revision {current_revision}, found {len(self.containers)} container image{'s' if len(self.containers) > 1 else ''} in total."
            )
            log.debug(f"Container names: {self.containers}")

            # Find out what the library directory is
            library_dir = Path(path_str) if (path_str := os.environ.get("NXF_SINGULARITY_LIBRARYDIR")) else None
            if library_dir and not library_dir.is_dir():
                # Since the library is read-only, if the directory isn't there, we can forget about it
                library_dir = None

            # Find out what the cache directory is
            cache_dir = Path(path_str) if (path_str := os.environ.get("NXF_SINGULARITY_CACHEDIR")) else None
            log.debug(f"NXF_SINGULARITY_CACHEDIR: {cache_dir}")
            if self.container_cache_utilisation in ["amend", "copy"]:
                if cache_dir:
                    if not cache_dir.is_dir():
                        log.debug(f"Cache directory not found, creating: {cache_dir}")
                        cache_dir.mkdir()
                else:
                    raise FileNotFoundError("Singularity cache is required but no '$NXF_SINGULARITY_CACHEDIR' set!")

            out_path_dir = self.get_container_output_dir().absolute()

            # Check that the directories exist
            if not out_path_dir.is_dir():
                log.debug(f"Output directory not found, creating: {out_path_dir}")
                out_path_dir.mkdir()

            container_fetcher: ContainerFetcher
            args: tuple[Any, ...]
            container_fetcher_constructor, args = {
                "singularity": (
                    SingularityFetcher,
                    (
                        self.container_library,
                        self.registry_set,
                        library_dir,
                        cache_dir,
                        self.container_cache_utilisation == "amend",
                        self.parallel,
                    ),
                ),
                "docker": (
                    DockerFetcher,
                    (
                        self.container_library,
                        self.registry_set,
                        self.parallel,
                    ),
                ),
            }[self.container_system]
            with container_fetcher_constructor(*args) as container_fetcher:
                container_fetcher.fetch_containers(
                    self.containers,
                    out_path_dir,
                    self.containers_remote,
                )

            # with DownloadProgress(disable=self.hide_progress) as progress:
            #     progress.add_main_task(
            #         total=len(self.containers),
            #     )
            #     # "Collecting container images",

            #     container_fetcher: ContainerFetcher
            #     if self.container_system == "singularity":
            #         container_fetcher = SingularityFetcher(
            # self.container_library,
            # self.registry_set,
            # progress,
            # library_dir,
            # cache_dir,
            # self.container_cache_utilisation == "amend",
            # parallel=self.parallel,
            #         )
            #     elif self.container_system == "docker":
            #         container_fetcher = DockerFetcher(
            #             self.container_library, self.registry_set, progress, parallel=self.parallel
            #         )
            #     container_fetcher.fetch_containers(
            #         self.containers,
            #         out_path_dir,
            #         self.containers_remote,
            #     )

    def compress_download(self):
        """Take the downloaded files and make a compressed .tar.gz archive."""
        log.debug(f"Creating archive: {self.output_filename}")

        # .tar.gz and .tar.bz2 files
        if self.compress_type in ["tar.gz", "tar.bz2"]:
            ctype = self.compress_type.split(".")[1]
            with tarfile.open(self.output_filename, f"w:{ctype}") as tar:
                tar.add(self.outdir, arcname=self.outdir.name)
            tar_flags = "xzf" if ctype == "gz" else "xjf"
            log.info(f"Command to extract files: [bright_magenta]tar -{tar_flags} {self.output_filename}[/]")

        # .zip files
        if self.compress_type == "zip":
            with ZipFile(self.output_filename, "w") as zip_file:
                # Iterate over all the files in directory
                for folder_name, _, filenames in self.outdir.walk():
                    for filename in filenames:
                        # create complete filepath of file in directory
                        file_path = folder_name / filename
                        # Add file to zip
                        zip_file.write(file_path)
            log.info(f"Command to extract files: [bright_magenta]unzip {self.output_filename}[/]")

        # Delete original files
        log.debug(f"Deleting uncompressed files: '{self.outdir}'")
        shutil.rmtree(self.outdir)

        # Calculate md5sum for output file
        log.info(f"MD5 checksum for '{self.output_filename}': [blue]{nf_core.utils.file_md5(self.output_filename)}[/]")
