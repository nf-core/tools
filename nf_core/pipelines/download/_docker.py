import logging
import shutil
from collections.abc import Iterable

from container_fetcher import ContainerFetcher

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
    ):
        """
        Intialize the docker image fetcher

        """
        super().__init__(
            container_library=container_library,
            registry_set=registry_set,
            progress=progress,
        )

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

    def construct_pull_command(self, container, output_path, address):
        docker_command = ["docker", "image", "pull", address]
        return docker_command
