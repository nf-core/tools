"""Apple Container fetcher for nf-core download.

Apple Container (https://github.com/apple/container) is a lightweight
container runtime for macOS on Apple Silicon. It uses standard OCI/Docker
images and provides its own CLI (``container``) with native ``pull`` and
``save`` commands for offline bundling.

Images are pulled and saved using the ``container`` CLI directly — no
Docker installation is required. Loading images on the target machine
uses ``container image load``.
"""

import logging
import shutil
from collections.abc import Iterable
from pathlib import Path

import rich.console

import nf_core.utils
from nf_core.pipelines.download.container_fetcher import ContainerFetcher
from nf_core.pipelines.download.docker import DockerFetcher
from nf_core.pipelines.download.utils import copy_container_load_scripts
from nf_core.utils import ContainerRegistryUrls

log = logging.getLogger(__name__)
stderr = rich.console.Console(
    stderr=True,
    highlight=False,
    force_terminal=nf_core.utils.rich_force_colors(),
)


class AppleContainerFetcher(DockerFetcher):
    """
    Fetcher for Apple Container images.

    Subclasses :class:`DockerFetcher` — uses the native Apple Container CLI
    (``container image pull`` / ``container image save``) instead of Docker.
    The cleanup step writes an Apple-Container-specific load script.
    """

    def __init__(
        self,
        outdir: Path,
        container_library: Iterable[str],
        registry_set: Iterable[str],
        parallel: int = 4,
        hide_progress: bool = False,
        image_arch: str = "linux/amd64",
    ):
        super().__init__(
            outdir=outdir,
            container_library=container_library,
            registry_set=registry_set,
            parallel=parallel,
            hide_progress=hide_progress,
        )
        # Override the container output directory name
        self._container_output_dir = outdir / "apple-container-images"
        # Architecture to request when pulling/saving images. Apple Container runs
        # amd64 images via emulation (matching the apple_container profile default),
        # so default to linux/amd64. Set to linux/arm64 for native arm64 images
        # (parity with the opt-in apple_container_wave profile).
        self.image_arch = image_arch

    def check_and_set_implementation(self) -> None:
        """
        Check if Apple Container CLI is installed and set the implementation.
        """
        container_binary = shutil.which("container")
        if not container_binary:
            raise OSError(
                "Apple Container CLI ('container') is needed to pull images, "
                "but it is not installed or not in $PATH.\n"
                "See: https://github.com/apple/container"
            )

        self.implementation = "container"

    def construct_pull_command(self, address: str) -> list[str]:
        """
        Construct the command to pull an image using Apple Container CLI.

        Args:
            address (str): The address of the container to pull.
        """
        pull_command = ["container", "image", "pull", "--platform", self.image_arch, address]
        log.debug(f"Apple Container command: {' '.join(pull_command)}")
        return pull_command

    def construct_save_command(self, output_path: Path, address: str) -> list[str]:
        """
        Construct the command to save an image using Apple Container CLI.

        Args:
            output_path (Path): The path to save the container image.
            address (str): The address of the container to save.
        """
        save_command = [
            "container",
            "image",
            "save",
            "--platform",
            self.image_arch,
            "--output",
            str(output_path),
            address,
        ]
        log.debug(f"Apple Container command: {' '.join(save_command)}")
        return save_command

    def gather_registries(self, workflow_directory: Path) -> set[str]:
        """
        Gather the registries for Apple Container downloads.

        Checks ``appleContainer.registry``, ``docker.registry``, and
        ``podman.registry`` keys from the workflow configuration.
        """
        registry_set = self.base_registry_set.copy()
        configured_registry_keys = ["appleContainer.registry", "docker.registry", "podman.registry"]

        registry_set |= self.gather_config_registries(
            workflow_directory,
            configured_registry_keys,
        )

        # Add the Seqera Docker container registry
        registry_set.add(ContainerRegistryUrls.SEQERA_DOCKER.value)
        return registry_set

    def cleanup(self) -> None:
        """
        Write the Apple Container load message (skipping the Docker-specific one).
        """
        # Call the grandparent cleanup directly to skip DockerFetcher.cleanup()
        ContainerFetcher.cleanup(self)
        self._write_apple_container_load_message()

    def _write_apple_container_load_message(self) -> None:
        """
        Inform the user how to load downloaded images into Apple Container.
        """
        img_dir = self.get_container_output_dir()
        apple_load_script, _ = copy_container_load_scripts("appleContainer", img_dir)
        indent = "    "
        stderr.print(
            "\n"
            f"{indent}Downloaded container images written to [magenta]'{img_dir}'[/].\n"
            f"{indent}After copying the pipeline and images to the target macOS machine, run\n\n"
            f"{indent}{indent}[green]./{apple_load_script}[/]\n\n"
            f"{indent}inside [magenta]'{img_dir}'[/] to load the images into Apple Container.\n"
        )
