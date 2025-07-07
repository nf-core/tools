import concurrent
import logging
import shutil
import subprocess
from collections.abc import Iterable

from nf_core.pipelines.download.container_fetcher import ContainerError, ContainerFetcher
from nf_core.pipelines.download.utils import (
    DownloadProgress,
)

log = logging.getLogger(__name__)


class DockerFetcher(ContainerFetcher):
    """
    Fetcher for Docker containers.
    """

    def __init__(
        self,
        container_library: Iterable[str],
        registry_set: Iterable[str],
        progress: DownloadProgress,
        max_workers: int = 4,
    ):
        """
        Intialize the docker image fetcher

        """
        super().__init__(
            container_library=container_library,
            registry_set=registry_set,
            progress=progress,
            max_workers=max_workers,
        )

        self.set_implementation()

    def set_implementation(self):
        if not shutil.which("docker"):
            raise OSError("Docker is needed to pull images, but it is not installed or not in $PATH")
        self.implementation = "docker"

    def clean_container_file_extension(self, container_fn):
        """
        This makes sure that the Docker container filename has a .tar extension
        """
        extension = ".tar"
        if container_fn.endswith(".tar"):
            container_fn.strip(".tar")
        # Strip : and / characters
        container_fn = container_fn.replace("/", "-").replace(":", "-")
        # Add file extension
        container_fn = container_fn + extension
        return container_fn

    def fetch_remote_containers(self, containers, max_workers=4):
        """
        Fetch remote containers in parallel.

        We first pull the images using the `docker image pull` command,
        then save them to a file using the `docker image save` command.
        Args:
            containers (Iterable[tuple[str, str]]): A list of tuples with the container name
        """
        self.pull_images(containers)
        self.save_images(containers, parallel_saves=max_workers)

    def construct_pull_command(self, address):
        pull_command = ["docker", "image", "pull", address]
        return pull_command

    def construct_save_command(self, output_path, address):
        save_command = [
            "docker",
            "image",
            "save",
            address,
            "--output",
            output_path,
        ]
        return save_command

    def save_image(self, container: str, output_path: str) -> None:
        """Save a Docker image that has been pulled to a file.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``biocontainers/name:varsion``
            out_path (str): The final target output path
            cache_path (str, None): The NXF_DOCKER_CACHEDIR path if set, None if not
        """
        log.debug(f"Saving Docker image '{container}' to {output_path}")
        address = container
        save_command = self.construct_save_command(output_path, address)
        self._run_docker_command(save_command, container, output_path, address, "save")

    def save_images(self, containers: Iterable[tuple[str, str]], parallel_saves) -> None:
        # if clause gives slightly better UX, because Download is no longer displayed if nothing is left to be downloaded.
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_saves) as pool:
            # Kick off concurrent downloads
            future_downloads = [
                pool.submit(self.save_image, container, output_path) for (container, output_path) in containers
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

    def pull_image(self, container: str, output_path: str, library: str) -> None:
        """Pull a docker image using ``docker pull``

        This function will try to pull the image from the specified library.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``nfcore/name:version``.
            library (list of str): A list of libraries to try for pulling the image.

        Raises:
            Various exceptions possible from `subprocess` execution of docker.
        """
        address = container

        pull_command = self.construct_pull_command(address)
        log.debug(f"Pulling docker image: {address}")
        log.debug(f"Docker command: {' '.join(pull_command)}")
        self._run_docker_command(pull_command, container, output_path, address, "docker_pull")

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
                    container_command=command,
                    error_msg=lines,
                    absolute_URI=address.startswith("docker://"),
                    registry=None,
                )

        self.progress.remove_task(task)
