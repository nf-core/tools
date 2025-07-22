import contextlib
import logging
import re
import shutil
from abc import ABC, abstractmethod
from collections.abc import Collection, Container, Generator, Iterable
from pathlib import Path
from typing import Optional, Union

import rich.progress

from nf_core.pipelines.download.utils import intermediate_file

log = logging.getLogger(__name__)


class ContainerProgress(rich.progress.Progress):
    """
    Custom Progress bar class, allowing us to have two progress
    bars with different columns / layouts.
    Also provide helper functions to control the top-level task.
    """

    def get_task_types_and_columns(self):
        """
        Gets the possible task types fo rthe
        """
        task_types_and_columns = {
            "summary": (
                "[magenta]{task.description}",
                rich.progress.BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.0f}%",
                "•",
                "[green]{task.completed}/{task.total} completed",
            ),
        }
        return task_types_and_columns

    def get_renderables(self) -> Generator[rich.table.Table, None, None]:
        self.columns: Iterable[Union[str, rich.progress.ProgressColumn]]
        for task in self.tasks:
            for task_type, columns in self.get_task_types_and_columns().items():
                if task.fields.get("progress_type") == task_type:
                    self.columns = columns

            yield self.make_tasks_table([task])

    # These two functions allow callers not having to track the main TaskID
    # They are pass-through functions to the rich.progress methods
    def add_main_task(self, **kwargs) -> rich.progress.TaskID:
        """
        Add a top-level task to the progress bar.
        This task will be used to track the overall progress of the container downloads.
        """
        self.main_task = self.add_task(
            "Container download",
            progress_type="summary",
            **kwargs,
        )
        return self.main_task

    def update_main_task(self, **kwargs) -> None:
        """
        Update the top-level task with new information.
        """
        self.update(self.main_task, **kwargs)

    @contextlib.contextmanager
    def sub_task(self, *args, **kwargs) -> Generator[rich.progress.TaskID, None, None]:
        """
        Context manager to create a sub-task under the main task.
        """
        task = self.add_task(*args, **kwargs)
        try:
            yield task
        finally:
            self.remove_task(task)


class ContainerFetcher(ABC):
    """Class to manage all Singularity operations for fetching containers.

    The guiding principles are that:
      - Container download/pull/copy methods are unaware of the concepts of
        "library" and "cache". They are just told to fetch a container and
        put it in a certain location.
      - Only the `fetch_containers` method is aware of the concepts of "library"
        and "cache". It is a sort of orchestrator that decides where to fetch
        each container and calls the appropriate methods.
      - All methods are integrated with a progress bar
    """

    def __init__(
        self,
        container_library: Iterable[str],
        registry_set: Iterable[str],
        progress_ctx: ContainerProgress,
        library_dir: Optional[Path],
        cache_dir: Optional[Path],
        amend_cachedir: bool,
        parallel: int = 4,
    ) -> None:
        self.container_library = list(container_library)
        self.registry_set = registry_set
        self._progress_ctx = progress_ctx
        self.progress: Optional[ContainerProgress] = None
        self.kill_with_fire = False
        self.implementation = None
        self.name = None
        self.library_dir = library_dir
        self.cache_dir = cache_dir
        self.amend_cachedir = amend_cachedir
        self.parallel = parallel

        self.check_and_set_implementation()

        self.progress = progress_ctx

    @property
    def progress(self) -> rich.progress.Progress:
        assert self._progress is not None  # mypy
        return self._progress

    @progress.setter
    def progress(self, progress: Optional[ContainerProgress]) -> None:
        self._progress = progress

    @abstractmethod
    def check_and_set_implementation(self) -> None:
        """
        Check if the container system is installed and available.

        Should update the `self.implementation` attribute with the found implementation

        Raises:
            OSError: If the container system is not installed or not in $PATH.
        """
        pass

    @abstractmethod
    def clean_container_file_extension(self, container_fn: str) -> str:
        """
        Clean the file extension of a container filename.

        Example implementation:

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

        Args:
            container_fn (str): The filename of the container.
        Returns:
            str: The cleaned filename with the appropriate extension.
        """
        pass

    # We have dropped the explicit registries from the modules in favor of the configurable registries.
    # Unfortunately, Nextflow still expects the registry to be part of the file name, so we need functions
    # to support accessing container images with different registries (or no registry).
    def get_container_filename(self, container: str) -> str:
        """Return the expected filename for a container.

        Supports docker, http, oras, and singularity URIs in `container`.

        Registry names provided in `registries` are removed from the filename to ensure that the same image
        is used regardless of the registry. Only registry names that are part of `registries` are considered.
        If the image name contains another registry, it will be kept in the filename.

        For instance, docker.io/nf-core/ubuntu:20.04 will be nf-core-ubuntu-20.04.img *only* if the registry
        contains "docker.io".
        """

        # Generate file paths
        # Based on simpleName() function in Nextflow code:
        # https://github.com/nextflow-io/nextflow/blob/671ae6d85df44f906747c16f6d73208dbc402d49/modules/nextflow/src/main/groovy/nextflow/container/SingularityCache.groovy#L69-L94
        out_name = container
        # Strip URI prefix
        out_name = re.sub(r"^.*:\/\/", "", out_name)

        # Clean the file extension. This method must be implemented
        # by any subclass
        out_name = self.clean_container_file_extension(out_name)

        # Trim potential registries from the name for consistency.
        # This will allow pipelines to work offline without symlinked images,
        # if docker.registry / singularity.registry are set to empty strings at runtime, which can be included in the HPC config profiles easily.
        if self.registry_set:
            # Create a regex pattern from the set of registries
            trim_pattern = "|".join(f"^{re.escape(registry)}-?".replace("/", "[/-]") for registry in self.registry_set)
            # Use the pattern to trim the string
            out_name = re.sub(f"{trim_pattern}", "", out_name)

        return out_name

    def fetch_containers(
        self,
        containers: Collection[str],
        output_dir: Path,
        exclude_list: Container[str],
    ):
        """
        This is the main entrypoint of the container fetcher. It goes through
        all the containers we find and does the appropriate action; copying
        from cache or fetching from a remote location
        """
        with self.progress:
            self.progress.add_main_task(total=0)

            # Check each container in the list and defer actions
            containers_remote_fetch: list[tuple[str, Path]] = []
            containers_copy: list[tuple[str, Path, Path]] = []

            # We may add more tasks as containers need to be copied between the various caches
            total_tasks = len(containers)

            for container in containers:
                container_filename = self.get_container_filename(container)

                # Files in the remote cache are already downloaded and can be ignored
                if container_filename in exclude_list:
                    log.debug(f"Skipping download of container '{container_filename}' as it is cached remotely.")
                    self.progress.update_main_task(advance=1, description=f"Skipping {container_filename}")
                    continue

                # Generate file paths for all three locations
                output_path = output_dir / container_filename

                if output_path.exists():
                    log.debug(f"Skipping download of container '{container_filename}' as it is in already present.")
                    self.progress.update_main_task(advance=1, description=f"{container_filename} exists at destination")
                    continue

                library_path = self.library_dir / container_filename if self.library_dir is not None else None
                cache_path = self.cache_dir / container_filename if self.cache_dir is not None else None

                # Get the container from the library
                if library_path and library_path.exists():
                    # Update the cache if needed
                    if cache_path and not cache_path.exists():
                        containers_copy.append((container, library_path, cache_path))
                        self.progress.update_main_task(total=total_tasks)

                    if not self.amend_cachedir:
                        # We are not just amending the cache directory, so the file should be copied to the output
                        containers_copy.append((container, library_path, output_path))

                # Get the container from the cache
                elif cache_path and cache_path.exists() and not self.amend_cachedir:
                    log.debug(f"Container '{container_filename}' found in cache at '{cache_path}'.")
                    containers_copy.append((container, cache_path, output_path))

                # Image is not in library or cache
                else:
                    # We treat downloading and pulling equivalently since this differs between docker and singularity.
                    # - Singularity images can either be downloaded from an http address, or pulled from a registry with `(singularity|apptainer) pull`
                    # - Docker images are always pulled, but needs the additional `docker image save` command for the image to be saved in the correct place
                    if cache_path:
                        # Download into the cache
                        containers_remote_fetch.append((container, cache_path))

                        # Do not copy to the output directory "(docker|singularity)-images" if we solely amending the cache
                        if not self.amend_cachedir:
                            containers_copy.append((container, cache_path, output_path))
                    else:
                        # There is no cache directory so download or pull directly to the output
                        containers_remote_fetch.append((container, output_path))

            # Fetch containers from a remote location
            if containers_remote_fetch:
                self.progress.update_main_task(description=f"Fetching {self.implementation} images")
                self.fetch_remote_containers(containers_remote_fetch, parallel=self.parallel)

            # Copy containers
            if containers_copy:
                self.progress.update_main_task(
                    description="Copying container images from/to cache", total=len(containers_copy), completed=0
                )
                for container, src_path, dest_path in containers_copy:
                    self.copy_image(container, src_path, dest_path)
                    self.progress.update_main_task(advance=1)

    @abstractmethod
    def fetch_remote_containers(self, containers: list[tuple[str, Path]], parallel: int = 4) -> None:
        """
        Fetch remote containers

        - Singularity: pull or download images, depending on what address we have
        - Docker: pull and save images

        This function should update the main progress task accordingly
        """
        pass

    def copy_image(self, container: str, src_path: Path, dest_path: Path) -> None:
        """Copy container image from one directory to another."""
        log.debug(f"Copying {container} from '{src_path.name}' to '{dest_path.name}'")

        with intermediate_file(dest_path) as dest_path_tmp:
            shutil.copyfile(src_path, dest_path_tmp.name)
