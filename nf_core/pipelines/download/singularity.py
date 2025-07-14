import itertools
import logging
import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path

from nf_core.pipelines.download.container_fetcher import ContainerFetcher
from nf_core.pipelines.download.utils import (
    FileDownloader,
)

log = logging.getLogger(__name__)


class SingularityFetcher(ContainerFetcher):
    """
    Fetcher for Docker containers.
    """

    def check_and_set_implementation(self):
        if shutil.which("singularity"):
            self.implementation = "singularity"
        elif shutil.which("apptainer"):
            self.implementation = "apptainer"
        else:
            raise OSError("Singularity/Apptainer is needed to pull images, but it is not installed or not in $PATH")

    def clean_container_file_extension(self, container_fn):
        """
        This makes sure that the Singularity container filename has the right file extension
        """
        # Detect file extension
        extension = ".img"
        if ".sif:" in container_fn:
            extension = ".sif"
            container_fn = container_fn.replace(".sif:", "-")
        elif container_fn.endswith(".sif"):
            extension = ".sif"
            container_fn = container_fn.replace(".sif", "")

        # Strip : and / characters
        container_fn = container_fn.replace("/", "-").replace(":", "-")
        # Add file extension
        container_fn = container_fn + extension
        return container_fn

    def fetch_remote_containers(self, containers, parallel=4):
        # Split the list of containers depending on whether we want to pull them or download them
        containers_pull = []
        containers_download = []
        for container, out_path in containers:
            # If the container is a remote image, we pull it
            if container.startswith("http"):
                containers_download.append((container, out_path))
            else:
                containers_pull.append((container, out_path))

        log.debug(containers)
        if containers_pull:
            # We only need to set the implementation if we are pulling images
            # -- a user could download images without having singularity/apptainer installed
            self.check_and_set_implementation()
            self.progress.update_main_task(description="Pulling singularity images")
            self.pull_images(containers_pull)

        if containers_download:
            self.progress.update_main_task(description="Downloading singularity images")
            self.download_images(containers_download, parallel_downloads=parallel)

    def symlink_registries(self, image_path: Path) -> None:
        """Create a symlink for each registry in the registry set that points to the image.

        The base image, e.g. ./nf-core-gatk-4.4.0.0.img will thus be symlinked as for example ./quay.io-nf-core-gatk-4.4.0.0.img
        by prepending each registry in `registries` to the image name.

        Unfortunately, the output image name may contain a registry definition (Singularity image pulled from depot.galaxyproject.org
        or older pipeline version, where the docker registry was part of the image name in the modules). Hence, it must be stripped
        before to ensure that it is really the base name.
        """

        # Create a regex pattern from the set, in case trimming is needed.
        trim_pattern = "|".join(f"^{re.escape(registry)}-?".replace("/", "[/-]") for registry in self.registry_set)

        for registry in self.registry_set:
            # Nextflow will convert it like this as well, so we need it mimic its behavior
            registry = registry.replace("/", "-")

            if not bool(re.search(trim_pattern, image_path.name)):
                symlink_name = Path("./", f"{registry}-{image_path.name}")
            else:
                trimmed_name = re.sub(f"{trim_pattern}", "", image_path.name)
                symlink_name = Path("./", f"{registry}-{trimmed_name}")

            symlink_full = Path(image_path.parent, symlink_name)
            target_name = Path("./", image_path.name)

            if not symlink_full.exists() and target_name != symlink_name:
                symlink_full.parent.mkdir(exist_ok=True)
                image_dir = os.open(image_path.parent, os.O_RDONLY)
                try:
                    os.symlink(
                        target_name,
                        symlink_name,
                        dir_fd=image_dir,
                    )
                    log.debug(f"Symlinked {target_name} as {symlink_name}.")
                finally:
                    os.close(image_dir)

    def construct_pull_command(self, output_path: Path, address: str):
        singularity_command = [self.implementation, "pull", "--name", str(output_path), address]
        return singularity_command

    def copy_image(self, container: str, src_path: Path, dest_path: Path):
        super().copy_image(container, src_path, dest_path)
        # For Singularity we need to create symlinks to ensure that the
        # images are found even with different registries being used.
        self.symlink_registries(dest_path)

    def download_images(
        self,
        containers_download: Iterable[tuple[str, Path]],
        parallel_downloads: int,
    ) -> None:
        downloader = FileDownloader(self.progress)

        def update_file_progress(input_params: tuple[str, Path], status: FileDownloader.Status) -> None:
            # try-except introduced in 4a95a5b84e2becbb757ce91eee529aa5f8181ec7
            # unclear why rich.progress may raise an exception here as it's supposed to be thread-safe
            try:
                self.progress.update_main_task(advance=1)
            except Exception as e:
                log.error(f"Error updating progress bar: {e}")

            if status == FileDownloader.Status.DONE:
                self.symlink_registries(input_params[1])

        downloader.download_files_in_parallel(containers_download, parallel_downloads, callback=update_file_progress)

    def pull_images(self, containers_pull: Iterable[tuple[str, Path]]) -> None:
        for container, output_path in containers_pull:
            # it is possible to try multiple registries / mirrors if multiple were specified.
            # Iteration happens over a copy of self.container_library[:], as I want to be able to remove failing registries for subsequent images.
            for library in self.container_library[:]:
                log.warning(f"Pulling '{container}' from '{library}' to '{output_path}'")
                try:
                    self.pull_image(container, output_path, library)
                    # Pulling the image was successful, no SingularityError was raised, break the library loop
                    break
                except SingularityError.ImageExistsError:
                    # Pulling not required

                    exit()
                    break
                except SingularityError.RegistryNotFoundError as e:
                    self.container_library.remove(library)
                    # The only library was removed
                    if not self.container_library:
                        log.error(e.message)
                        log.error(e.helpmessage)
                        raise OSError from e
                    else:
                        # Other libraries can be used
                        continue
                except SingularityError.ImageNotFoundError as e:
                    # Try other registries
                    if e.error_log.absolute_URI:
                        break  # there no point in trying other registries if absolute URI was specified.
                    else:
                        continue
                except SingularityError.InvalidTagError:
                    # Try other registries
                    continue
                except SingularityError.OtherError as e:
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

    def pull_image(self, container: str, output_path: Path, library: str) -> None:
        """Pull a singularity image using ``singularity pull``

        Attempt to use a local installation of singularity to pull the image.

        Args:
            container (str): A pipeline's container name. Usually it is of similar format
                to ``nfcore/name:version``.
            library (list of str): A list of libraries to try for pulling the image.

        Raises:
            Various exceptions possible from `subprocess` execution of Singularity.
        """
        # Sometimes, container still contain an explicit library specification, which
        # resulted in attempted pulls e.g. from docker://quay.io/quay.io/qiime2/core:2022.11
        # Thus, if an explicit registry is specified, the provided -l value is ignored.
        # Additionally, check if the container to be pulled is native Singularity: oras:// protocol.
        container_parts = container.split("/")
        if len(container_parts) > 2:
            address = container if container.startswith("oras://") else f"docker://{container}"
            absolute_URI = True
        else:
            address = f"docker://{library}/{container.replace('docker://', '')}"
            absolute_URI = False
        log.warning(f"Pulling singularity image {container} from {address} to {output_path}")
        with self.progress.sub_task(
            container,
            start=False,
            total=False,
            progress_type="singularity_pull",
            current_log="",
        ) as task:
            singularity_command = self.construct_pull_command(output_path, address)

            log.debug(f"Building singularity image: {address}")
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
                        self.progress.update(task, current_log=line.strip())

            if lines:
                # something went wrong with the container retrieval
                log.debug(f"Singularity pull output: {lines}")
                if any("FATAL: " in line for line in lines):
                    raise SingularityError(
                        container=container,
                        registry=library,
                        address=address,
                        absolute_URI=absolute_URI,
                        out_path=output_path,
                        command=singularity_command,
                        error_msg=lines,
                    )

            self.symlink_registries(output_path)


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
        command,
        error_msg,
    ):
        self.container = container
        self.registry = registry
        self.address = address
        self.absolute_URI = absolute_URI
        self.out_path = out_path
        self.command = command
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
        # Loop through the error messages and patterns. Since we want to have the option of
        # no matches at all, we use itertools.product to allow for the use of the for ... else construct.
        for line, (pattern, error_class) in itertools.product(error_msg, error_patterns.items()):
            if re.search(pattern, line):
                self.error_type = error_class(self)
                break
        else:
            self.error_type = self.OtherError(self)

        log.error(self.error_type.message)
        log.info(self.error_type.helpmessage)
        log.debug(f"Failed command:\n{' '.join(command)}")
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
            self.helpmessage = f'Please chose a different library than {self.error_log.registry}\nor try to locate the "{self.error_log.address.split(":")[-1]}" version of "{self.error_log.container}" manually.\nPlease troubleshoot the command \n"{" ".join(self.error_log.command)}" manually.\n'
            super().__init__(self.message)

    class ImageExistsError(FileExistsError):
        """Image already exists in cache/output directory."""

        def __init__(self, error_log):
            self.error_log = error_log
            self.message = (
                f'[bold red]"{self.error_log.container}" already exists at destination and cannot be pulled[/]\n'
            )
            self.helpmessage = f'Saving image of "{self.error_log.container}" failed, because "{self.error_log.out_path}" exists.\nPlease troubleshoot the command \n"{" ".join(self.error_log.command)}" manually.\n'
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
                self.helpmessage = f'Pulling of "{self.error_log.container}" failed.\nPlease troubleshoot the command \n"{" ".join(self.error_log.command)}" manually.\n'
            else:
                self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
                self.helpmessage = (
                    f'Please try to rerun \n"{" ".join(self.error_log.command)}" manually with a different registry.f\n'
                )

            super().__init__(self.message, self.helpmessage, self.error_log)
