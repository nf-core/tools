import concurrent.futures
import logging
import os
import re
import shutil
import subprocess
from collections.abc import Collection, Container, Iterable
from typing import Optional

from nf_core.pipelines.download.utils import DownloadProgress, intermediate_file

log = logging.getLogger(__name__)


class DockerFetcher:
    """Class to manage all Docker operations for fetching containers.

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
    ) -> None:
        self.container_library = list(container_library)
        self.registry_set = registry_set
        self.progress = progress
        self.kill_with_fire = False

    def get_container_filename(self, container: str) -> str:
        """Check Docker cache for image, copy to destination folder if found.

        Args:
            container (str):    A pipeline's container name. Can be direct download URL
                                or a Docker Hub repository ID.

        Returns:
            # TODO
            tuple (str, str):   Returns a tuple of (out_path, cache_path).
        """

        # Generate file paths
        # Based on simpleName() function in Nextflow code:
        # https://github.com/nextflow-io/nextflow/blob/671ae6d85df44f906747c16f6d73208dbc402d49/modules/nextflow/src/main/groovy/nextflow/container/SingularityCache.groovy#L69-L94
        out_name = container
        # Strip URI prefix
        out_name = re.sub(r"^.*:\/\/", "", out_name)
        # Detect file extension
        extension = ".tar"
        if out_name.endswith(".tar"):
            extension = ".tar"
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
            trim_pattern = "|".join(f"^{re.escape(registry)}-?".replace("/", "[/-]") for registry in self.registry_set)
            # Use the pattern to trim the string
            out_name = re.sub(f"{trim_pattern}", "", out_name)

        return out_name

    def download_images(
        self,
        containers_download: Iterable[tuple[str, str]],
        parallel_downloads: int,
    ) -> None:
        # if clause gives slightly better UX, because Download is no longer displayed if nothing is left to be downloaded.
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_downloads) as pool:
            # Kick off concurrent downloads
            future_downloads = [
                pool.submit(self.download_image, container, output_path)
                for (container, output_path) in containers_download
            ]

            # Make ctrl-c work with multi-threading
            self.kill_with_fire = False

            try:
                # Iterate over each threaded download, waiting for them to finish
                for future in concurrent.futures.as_completed(future_downloads):
                    future.result()
                    try:
                        self.progress.update_main_task(advance=1)
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

    def download_image(self, container: str, output_path: str) -> None:
        """Download a Docker image from the web.

        Use docker cli to download the file.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``biocontainers/name:varsion``
            out_path (str): The final target output path
            cache_path (str, None): The NXF_DOCKER_CACHEDIR path if set, None if not
        """
        log.debug(f"Downloading Docker image '{container}' to {output_path}")
        address = container

        if shutil.which("docker"):
            download_command = [
                "docker",
                "image",
                "save",
                address,
                "--output",
                output_path,
            ]
            self._run_docker_command(download_command, container, output_path, address, "download")
        else:
            raise OSError("Docker is needed to pull images, but it is not installed or not in $PATH")

    def pull_images(self, containers_pull: Iterable[tuple[str, str]]) -> None:
        for container, output_path in containers_pull:
            # it is possible to try multiple registries / mirrors if multiple were specified.
            # Iteration happens over a copy of self.container_library[:], as I want to be able to remove failing registries for subsequent images.
            for library in self.container_library[:]:
                try:
                    self.pull_image(container, output_path, library)
                    # Pulling the image was successful, no ContainerError was raised, break the library loop
                    break
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
                    f"Not able to pull image of {container}. Service might be down or internet connection is dead."
                )
            # Task should advance in any case. Failure to pull will not kill the download process.
            self.progress.update_main_task(advance=1)

    def _run_docker_command(
        self,
        command: list[str],
        container: str,
        output_path: str,
        address: str,
        task_name: str,
    ) -> None:
        """
        Internal command to run docker commands and error handle them properly
        """
        # Progress bar to show that something is happening
        nice_name = container.split("/")[-1][:50]
        task = self.progress.add_task(
            nice_name,
            start=False,
            total=False,
            progress_type=task_name,
            current_log="",
        )
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        ) as proc:
            lines = []
            if proc.stdout is not None:
                for line in proc.stdout:
                    lines.append(line)
                    self.progress.update(task, current_log=line.strip())

        if lines:
            # something went wrong with the container retrieval
            possible_error_lines = {
                "invalid reference format",
                "Error response from daemon:",
            }
            if any(pel in line for pel in possible_error_lines for line in lines):
                self.progress.remove_task(task)
                raise ContainerError(
                    container=container,
                    address=address,
                    out_path=output_path,
                    command=command,
                    error_msg=lines,
                    absolute_URI=address.startswith("docker://"),
                )
            else:
                log.warning("Everything is fine")

        self.progress.remove_task(task)

    def pull_image(self, container: str, output_path: str, library: str) -> None:
        """Pull a docker image using ``docker pull``

        Attempt to use a local installation of docker to pull the image.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``nfcore/name:version``.
            library (list of str): A list of libraries to try for pulling the image.

        Raises:
            Various exceptions possible from `subprocess` execution of docker.
        """
        address = container

        if shutil.which("docker"):
            docker_command = ["docker", "image", "pull", address]
            log.debug(f"Building docker image: {address}")
            log.debug(f"Docker command: {' '.join(docker_command)}")
            self._run_docker_command(docker_command, container, output_path, address, "docker_pull")
        else:
            raise OSError("Docker is needed to pull images, but it is not installed or not in $PATH")

    def copy_image(self, container: str, src_path: str, dest_path: str) -> None:
        """Copy Docker image from one directory to another."""
        log.debug(f"Copying {container} from '{os.path.basename(src_path)}' to '{os.path.basename(dest_path)}'")

        with intermediate_file(dest_path) as dest_path_tmp:
            shutil.copyfile(src_path, dest_path_tmp.name)

    def fetch_containers(
        self,
        containers: Collection[str],
        output_dir: str,
        exclude_list: Container[str],
        library_dir: Optional[str],
        cache_dir: Optional[str],
        amend_cachedir: bool,
    ):
        # Check each container in the list and defer actions
        containers_download: list[tuple[str, str]] = []
        containers_pull: list[tuple[str, str]] = []
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

            library_path = os.path.join(library_dir, container_filename) if library_dir else None
            cache_path = os.path.join(cache_dir, container_filename) if cache_dir else None

            # get the container from the library
            if library_path and os.path.exists(library_path):
                containers_copy.append((container, library_path, output_path))
                # update the cache if needed
                if cache_path and amend_cachedir and not os.path.exists(cache_path):
                    containers_copy.append((container, library_path, cache_path))
                    total_tasks += 1
                    self.progress.update_main_task(total=total_tasks)

            # get the container from the cache
            elif cache_path and os.path.exists(cache_path):
                containers_copy.append((container, cache_path, output_path))

            # no library or cache
            else:
                # Handle container download, docker needs images to be pulled before it can save them
                log.warning(f"Cache path {cache_path} and amend cachedir {amend_cachedir}")
                if cache_path and amend_cachedir:
                    # download into the cache
                    containers_pull.append((container, cache_path))
                    containers_download.append((container, cache_path))
                    # and copy from the cache to the output
                    containers_copy.append((container, cache_path, output_path))
                    total_tasks += 1
                    self.progress.update_main_task(total=total_tasks)

                else:
                    # download or pull directly to the output
                    containers_pull.append((container, output_path))

        # Pull all containers
        if containers_pull:
            if not shutil.which("docker"):
                raise OSError("Docker is needed to pull images, but it is not installed or not in $PATH")
            self.progress.update_main_task(description="Pulling docker images")
            self.pull_images(containers_pull)

        # Download all containers
        if containers_download:
            self.progress.update_main_task(description="Downloading docker images")
            self.download_images(containers_download, parallel_downloads=4)

        # Copy all containers
        self.progress.update_main_task(description="Copying docker images from/to cache")
        for container, src_path, dest_path in containers_copy:
            self.copy_image(container, src_path, dest_path)
            self.progress.update_main_task(advance=1)


# Distinct errors for the container download, required for acting on the exceptions
class ContainerError(Exception):
    """A class of errors related to pulling containers with Docker"""

    def __init__(
        self,
        container,
        address,
        absolute_URI,
        out_path,
        command,
        error_msg,
    ):
        self.container = container
        self.address = address
        self.absolute_URI = absolute_URI
        self.out_path = out_path
        self.command = command
        self.error_msg = error_msg

        for line in error_msg:
            if "reference does not exist" in line:
                self.error_type = self.ImageNotPulledError(self)
            if "repository does not exist" in line:
                self.error_type = self.ImageNotFoundError(self)
            if "manifest unknown" in line:
                self.error_type = self.InvalidTagError(self)
            else:
                continue
        else:
            self.error_type = self.OtherError(self)

        log.error(self.error_type.message)
        log.info(self.error_type.helpmessage)
        log.debug(f"Failed command:\n{' '.join(self.command)}")
        log.debug(f"Docker error messages:\n{''.join(error_msg)}")

        raise self.error_type

    class ImageNotPulledError(AttributeError):
        """Docker is trying to save an image that was not pulled"""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = f'[bold red] Cannot save "{self.error_log.container}" as it was not pulled [/]\n'
            self.helpmessage = "Please pull the image first and confirm that it can be pulled.\n"
            super().__init__(self.message)

    class ImageNotFoundError(FileNotFoundError):
        """The image can not be found in the registry"""

        def __init__(self, error_log):
            self.error_log = error_log
            if not self.error_log.absolute_URI:
                self.message = (
                    f'[bold red]"Pulling "{self.error_log.container}" from "{self.error_log.address}" failed.[/]\n'
                )
                self.helpmessage = f'Saving image of "{self.error_log.container}" failed.\nPlease troubleshoot the command \n"{" ".join(self.error_log.command)}" manually.f\n'
            else:
                self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
                self.helpmessage = (
                    f'Please try to rerun \n"{" ".join(self.error_log.command)}" manually with a different registry.f\n'
                )

            super().__init__(self.message)

    class InvalidTagError(AttributeError):
        """Image and registry are valid, but the (version) tag is not"""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = f'[bold red]"{self.error_log.address.split(":")[-1]}" is not a valid tag of "{self.error_log.container}"[/]\n'
            self.helpmessage = f'Please chose a different library than {self.error_log.address}\nor try to locate the "{self.error_log.address.split(":")[-1]}" version of "{self.error_log.container}" manually.\nPlease troubleshoot the command \n"{" ".join(self.error_log.command)}" manually.\n'
            super().__init__(self.message)

    class OtherError(RuntimeError):
        """Undefined error with the container"""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
            self.helpmessage = (
                f'Please try to rerun \n"{" ".join(self.error_log.command)}" manually with a different registry.\n'
            )
            super().__init__(self.message, self.helpmessage, self.error_log)
