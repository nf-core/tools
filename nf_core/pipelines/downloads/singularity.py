import logging
import os
import re
import shutil
import subprocess
from typing import Collection, Container, Iterable, List, Optional, Tuple

from nf_core.pipelines.downloads.utils import DownloadProgress, FileDownloader, intermediate_file

log = logging.getLogger(__name__)


# We have dropped the explicit registries from the modules in favor of the configurable registries.
# Unfortunately, Nextflow still expects the registry to be part of the file name, so we need functions
# to support accessing container images with different registries (or no registry).


def get_container_filename(container: str, registries: Iterable[str]) -> str:
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
    if registries:
        # Create a regex pattern from the set of registries
        trim_pattern = "|".join(f"^{re.escape(registry)}-?".replace("/", "[/-]") for registry in registries)
        # Use the pattern to trim the string
        out_name = re.sub(f"{trim_pattern}", "", out_name)

    return out_name


def symlink_registries(image_path: str, registries: Iterable[str]) -> None:
    """Create a symlink for each registry in the registry set that points to the image.

    The base image, e.g. ./nf-core-gatk-4.4.0.0.img will thus be symlinked as for example ./quay.io-nf-core-gatk-4.4.0.0.img
    by prepending each registry in `registries` to the image name.

    Unfortunately, the output image name may contain a registry definition (Singularity image pulled from depot.galaxyproject.org
    or older pipeline version, where the docker registry was part of the image name in the modules). Hence, it must be stripped
    before to ensure that it is really the base name.
    """

    # Create a regex pattern from the set, in case trimming is needed.
    trim_pattern = "|".join(f"^{re.escape(registry)}-?".replace("/", "[/-]") for registry in registries)

    for registry in registries:
        # Nextflow will convert it like this as well, so we need it mimic its behavior
        registry = registry.replace("/", "-")

        if not bool(re.search(trim_pattern, os.path.basename(image_path))):
            symlink_name = os.path.join("./", f"{registry}-{os.path.basename(image_path)}")
        else:
            trimmed_name = re.sub(f"{trim_pattern}", "", os.path.basename(image_path))
            symlink_name = os.path.join("./", f"{registry}-{trimmed_name}")

        symlink_full = os.path.join(os.path.dirname(image_path), symlink_name)
        target_name = os.path.join("./", os.path.basename(image_path))

        if not os.path.exists(symlink_full) and target_name != symlink_name:
            os.makedirs(os.path.dirname(symlink_full), exist_ok=True)
            image_dir = os.open(os.path.dirname(image_path), os.O_RDONLY)
            try:
                os.symlink(
                    target_name,
                    symlink_name,
                    dir_fd=image_dir,
                )
                log.debug(f"Symlinked {target_name} as {symlink_name}.")
            finally:
                os.close(image_dir)


class SingularityFetcher:
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
        self, container_library: Iterable[str], registry_set: Iterable[str], progress: DownloadProgress
    ) -> None:
        self.container_library = list(container_library)
        self.registry_set = registry_set
        self.progress = progress
        self.kill_with_fire = False

    def download_images(
        self,
        containers_download: Iterable[Tuple[str, str]],
        parallel_downloads: int,
    ) -> None:
        downloader = FileDownloader(self.progress)
        for output_path in downloader.download_files_in_parallel(containers_download, parallel_downloads):
            # try-except introduced in 4a95a5b84e2becbb757ce91eee529aa5f8181ec7
            # unclear why rich.progress may raise an exception here as it's supposed to be thread-safe
            try:
                self.progress.update_main_task(advance=1)
            except Exception as e:
                log.error(f"Error updating progress bar: {e}")

            symlink_registries(output_path, self.registry_set)

    def pull_images(self, containers_pull: Iterable[Tuple[str, str]]) -> None:
        for container, output_path in containers_pull:
            # it is possible to try multiple registries / mirrors if multiple were specified.
            # Iteration happens over a copy of self.container_library[:], as I want to be able to remove failing registries for subsequent images.
            for library in self.container_library[:]:
                try:
                    self.pull_image(container, output_path, library)
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
                    f"Not able to pull image of {container}. Service might be down or internet connection is dead."
                )
            # Task should advance in any case. Failure to pull will not kill the download process.
            self.progress.update_main_task(advance=1)

    def pull_image(self, container: str, output_path: str, library: str) -> None:
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

        with self.progress.sub_task(
            container,
            start=False,
            total=False,
            progress_type="singularity_pull",
            current_log="",
        ) as task:
            with intermediate_file(output_path) as output_path_tmp:
                if shutil.which("singularity"):
                    singularity_command = [
                        "singularity",
                        "pull",
                        "--name",
                        output_path_tmp.name,
                        address,
                    ]
                elif shutil.which("apptainer"):
                    singularity_command = ["apptainer", "pull", "--name", output_path_tmp.name, address]
                else:
                    raise OSError(
                        "Singularity/Apptainer is needed to pull images, but it is not installed or not in $PATH"
                    )
                log.debug(f"Building singularity image: {address}")
                log.debug(f"Singularity command: {' '.join(singularity_command)}")

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
                    if any("FATAL: " in line for line in lines):
                        raise ContainerError(
                            container=container,
                            registry=library,
                            address=address,
                            absolute_URI=absolute_URI,
                            out_path=output_path,
                            singularity_command=singularity_command,
                            error_msg=lines,
                        )

            symlink_registries(output_path, self.registry_set)

    def copy_image(self, container: str, src_path: str, dest_path: str) -> None:
        """Copy Singularity image from one directory to another."""
        log.debug(f"Copying {container} from '{os.path.basename(src_path)}' to '{os.path.basename(dest_path)}'")

        with intermediate_file(dest_path) as dest_path_tmp:
            shutil.copyfile(src_path, dest_path_tmp.name)

        # Create symlinks to ensure that the images are found even with different registries being used.
        symlink_registries(dest_path, self.registry_set)

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
        containers_download: List[Tuple[str, str]] = []
        containers_pull: List[Tuple[str, str]] = []
        containers_copy: List[Tuple[str, str, str]] = []

        # We may add more tasks as containers need to be copied between the various caches
        total_tasks = len(containers)

        for container in containers:
            container_filename = get_container_filename(container, self.registry_set)

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
                # fetch method (download or pull)
                if container.startswith("http"):
                    fetch_list = containers_download
                else:
                    fetch_list = containers_pull

                if cache_path and amend_cachedir:
                    # download into the cache
                    fetch_list.append((container, cache_path))
                    # and copy from the cache to the output
                    containers_copy.append((container, cache_path, output_path))
                    total_tasks += 1
                    self.progress.update_main_task(total=total_tasks)

                else:
                    # download or pull directly to the output
                    fetch_list.append((container, output_path))

        # Download all containers
        if containers_download:
            self.progress.update_main_task(description="Downloading singularity images")
            self.download_images(containers_download, parallel_downloads=4)

        # Pull all containers
        if containers_pull:
            if not (shutil.which("singularity") or shutil.which("apptainer")):
                raise OSError("Singularity/Apptainer is needed to pull images, but it is not installed or not in $PATH")
            self.progress.update_main_task(description="Pulling singularity images")
            self.pull_images(containers_pull)

        # Copy all containers
        self.progress.update_main_task(description="Copying singularity images from/to cache")
        for container, src_path, dest_path in containers_copy:
            self.copy_image(container, src_path, dest_path)
            self.progress.update_main_task(advance=1)


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
            elif re.search(r"ORAS\sSIF\simage\sshould\shave\sa\ssingle\slayer", line):
                self.error_type = self.NoSingularityContainerError(self)
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
        log.debug(f"Failed command:\n{' '.join(singularity_command)}")
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
                self.helpmessage = f'Pulling of "{self.error_log.container}" failed.\nPlease troubleshoot the command \n"{" ".join(self.error_log.singularity_command)}" manually.\n'
            else:
                self.message = f'[bold red]"The pipeline requested the download of non-existing container image "{self.error_log.address}"[/]\n'
                self.helpmessage = f'Please try to rerun \n"{" ".join(self.error_log.singularity_command)}" manually with a different registry.f\n'

            super().__init__(self.message, self.helpmessage, self.error_log)
