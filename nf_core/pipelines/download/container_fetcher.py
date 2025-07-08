import logging
import os
import re
import shutil
from abc import abstractmethod
from collections.abc import Collection, Container, Iterable
from typing import Optional

from nf_core.pipelines.download.utils import (
    DownloadProgress,
    intermediate_file,
)

log = logging.getLogger(__name__)


class ContainerFetcher:
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
        progress: DownloadProgress,
        library_dir: Optional[str],
        cache_dir: Optional[str],
        amend_cachedir: bool,
        parallel: int = 4,
    ) -> None:
        self.container_library = list(container_library)
        self.registry_set = registry_set
        self.progress = progress
        self.kill_with_fire = False
        self.implementation = None
        self.name = None
        self.library_dir = library_dir
        self.cache_dir = cache_dir
        self.amend_cachedir = amend_cachedir
        self.parallel = parallel

        self.check_and_set_implementation()

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
        output_dir: str,
        exclude_list: Container[str],
    ):
        """
        This is the main entrypoint of the container fetcher. It goes through
        all the containers we find and does the appropriate action; copying
        from cache or fetching from a remote location
        """
        # Check each container in the list and defer actions
        containers_remote_fetch: list[tuple[str, str]] = []
        containers_copy: list[tuple[str, str, str]] = []

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
            output_path = os.path.join(output_dir, container_filename)

            if os.path.exists(output_path):
                log.debug(f"Skipping download of container '{container_filename}' as it is in already present.")
                self.progress.update_main_task(advance=1, description=f"{container_filename} exists at destination")
                continue

            library_path = os.path.join(self.library_dir, container_filename) if self.library_dir else None
            cache_path = os.path.join(self.cache_dir, container_filename) if self.cache_dir else None

            # get the container from the library
            if library_path and os.path.exists(library_path):
                containers_copy.append((container, library_path, output_path))
                # update the cache if needed
                if cache_path and not self.amend_cachedir and not os.path.exists(cache_path):
                    containers_copy.append((container, library_path, cache_path))
                    total_tasks += 1
                    self.progress.update_main_task(total=total_tasks)

            # get the container from the cache
            elif cache_path and os.path.exists(cache_path):
                log.debug(f"Container '{container_filename}' found in cache at '{cache_path}'.")
                containers_copy.append((container, cache_path, output_path))
            # no library or cache
            else:
                # We treat downloading and pulling equivalently since this differs between docker and singularity.
                # - Singularity images can either be downloaded from an http address, or pulled from a registry with `(singularity|apptainer) pull`
                # - Docker images are always pulled, but needs the additional `docker image save` command for the image to be saved in the correct place
                if cache_path:
                    # download into the cache
                    containers_remote_fetch.append((container, cache_path))
                    # only copy to the output if we are not amending the cache
                    if not self.amend_cachedir:
                        containers_copy.append((container, cache_path, output_path))
                    total_tasks += 1
                    self.progress.update_main_task(total=total_tasks)
                else:
                    # download or pull directly to the output
                    containers_remote_fetch.append((container, output_path))

        # Fetch containers from a remote location
        if containers_remote_fetch:
            self.progress.update_main_task(description=f"Fetching {self.implementation} images")
            self.fetch_remote_containers(containers_remote_fetch, parallel=self.parallel)

        # Copy containers
        self.progress.update_main_task(description="Copying container images from/to cache")
        for container, src_path, dest_path in containers_copy:
            self.copy_image(container, src_path, dest_path)
            self.progress.update_main_task(advance=1)

    @abstractmethod
    def fetch_remote_containers(self, containers: list[tuple[str, str]], parallel=4):
        """
        Fetch remote containers

        - Singularity: pull or download images, depending on what address we have
        - Docker: pull and save images
        """
        pass

    def get_address(self, container: str, library: str) -> tuple[str, bool]:
        """
        Get the address of the container based on its format.

        Args:
            container (str): The container name

        Returns:
            tuple[str, bool]: The address of the container and a boolean indicating if it is an absolute URI.
        """
        container_parts = container.split("/")
        if len(container_parts) > 2:
            address = container if container.startswith("oras://") else f"docker://{container}"
            absolute_URI = True
        else:
            address = f"docker://{library}/{container.replace('docker://', '')}"
            absolute_URI = False
        return address, absolute_URI

    def copy_image(self, container: str, src_path: str, dest_path: str) -> None:
        """Copy container image from one directory to another."""
        log.debug(f"Copying {container} from '{os.path.basename(src_path)}' to '{os.path.basename(dest_path)}'")

        with intermediate_file(dest_path) as dest_path_tmp:
            shutil.copyfile(src_path, dest_path_tmp.name)


# Distinct errors for the Singularity container download, required for acting on the exceptions
class SingularityError(Exception):
    """A class of errors related to pulling containers with Singularity/Apptainer"""

    def __init__(
        self,
        container,
        registry,
        address,
        absolute_URI,
        out_path,
        container_command,
        error_msg,
    ):
        self.container = container
        self.registry = registry
        self.address = address
        self.absolute_URI = absolute_URI
        self.out_path = out_path
        self.container_command = container_command
        self.error_msg = error_msg
        self.patterns = []

        error_patterns = {
            # The registry does not resolve to a valid IP address
            r"dial\stcp.*no\ssuch\shost": self.RegistryNotFoundError,
            #
            # Unfortunately, every registry seems to return an individual error here:
            # Docker.io: denied: requested access to the resource is denied
            #                    unauthorized: authentication required
            # Quay.io: StatusCode: 404,  <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">\n']
            # ghcr.io: Requesting bearer token: invalid status code from registry 400 (Bad Request)
            #
            r"requested\saccess\sto\sthe\sresource\sis\sdenied": self.ImageNotFoundError,  # Docker.io
            r"StatusCode:\s404": self.ImageNotFoundError,  # Quay.io
            r"invalid\sstatus\scode\sfrom\sregistry\s400": self.ImageNotFoundError,  # ghcr.io
            r"400|Bad\s?Request": self.ImageNotFoundError,  # ghcr.io
            # The image and registry are valid, but the (version) tag is not
            r"manifest\sunknown": self.InvalidTagError,
            # The container image is no native Singularity Image Format.
            r"ORAS\sSIF\simage\sshould\shave\sa\ssingle\slayer": self.NoSingularityContainerError,
            # The image file already exists in the output directory
            r"Image\sfile\salready\sexists": self.ImageExistsError,
        }
        for line in error_msg:
            for pattern, error_class in error_patterns.items():
                if re.search(pattern, line):
                    self.error_type = error_class(self)
                    break
        else:
            self.error_type = self.OtherError(self)

        log.error(self.error_type.message)
        log.info(self.error_type.helpmessage)
        log.debug(f"Failed command:\n{' '.join(container_command)}")
        log.debug(f"Singularity error messages:\n{''.join(error_msg)}")

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
                self.helpmessage = f'Saving image of "{self.error_log.container}" failed.\nPlease troubleshoot the command \n"{" ".join(self.error_log.container_command)}" manually.f\n'
            else:
                self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
                self.helpmessage = f'Please try to rerun \n"{" ".join(self.error_log.container_command)}" manually with a different registry.f\n'

            super().__init__(self.message)

    class InvalidTagError(AttributeError):
        """Image and registry are valid, but the (version) tag is not"""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = f'[bold red]"{self.error_log.address.split(":")[-1]}" is not a valid tag of "{self.error_log.container}"[/]\n'
            self.helpmessage = f'Please chose a different library than {self.error_log.registry}\nor try to locate the "{self.error_log.address.split(":")[-1]}" version of "{self.error_log.container}" manually.\nPlease troubleshoot the command \n"{" ".join(self.error_log.container_command)}" manually.\n'
            super().__init__(self.message)

    class ImageExistsError(FileExistsError):
        """Image already exists in cache/output directory."""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = (
                f'[bold red]"{self.error_log.container}" already exists at destination and cannot be pulled[/]\n'
            )
            self.helpmessage = f'Saving image of "{self.error_log.container}" failed, because "{self.error_log.out_path}" exists.\nPlease troubleshoot the command \n"{" ".join(self.error_log.container_command)}" manually.\n'
            super().__init__(self.message)

    class NoSingularityContainerError(RuntimeError):
        """The container image is no native Singularity Image Format."""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = (
                f'[bold red]"{self.error_log.container}" is no valid Singularity Image Format container.[/]\n'
            )
            self.helpmessage = f"Pulling \"{self.error_log.container}\" failed, because it appears invalid. To convert from Docker's OCI format, prefix the URI with 'docker://' instead of 'oras://'.\n"
            super().__init__(self.message)

    class OtherError(RuntimeError):
        """Undefined error with the container"""

        def __init__(self, error_log):
            self.error_log = error_log
            if not self.error_log.absolute_URI:
                self.message = f'[bold red]"{self.error_log.container}" failed for unclear reasons.[/]\n'
                self.helpmessage = f'Pulling of "{self.error_log.container}" failed.\nPlease troubleshoot the command \n"{" ".join(self.error_log.container_command)}" manually.\n'
            else:
                self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
                self.helpmessage = f'Please try to rerun \n"{" ".join(self.error_log.container_command)}" manually with a different registry.f\n'

            super().__init__(self.message, self.helpmessage, self.error_log)
