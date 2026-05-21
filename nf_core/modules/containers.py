import logging
import os
import re
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests
import rich.progress
import yaml
from rich.pretty import pretty_repr

from nf_core.components.components_utils import read_meta_yml
from nf_core.components.components_utils import yaml as ruamel_yaml
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.lint import ModuleLint
from nf_core.modules.modules_utils import filter_modules_by_name, prompt_module_selection, scan_modules_dir
from nf_core.pipelines.lint_utils import run_prettier_on_file
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, run_cmd

log = logging.getLogger(__name__)


class ModuleContainers:
    """
    Helpers for building, linting and listing module containers.
    """

    IMAGE_KEY = "name"
    BUILD_ID_KEY = "build_id"
    SCAN_ID_KEY = "scan_id"
    LOCK_FILE_KEY = "lock_file"
    HTTPS_URL_KEY = "https"

    def __init__(
        self, module: str | None, directory: str | Path = ".", all_modules: bool = False, verbose: bool = False
    ):
        from nf_core.components.components_utils import get_repo_info

        self.directory = Path(directory)
        self.verbose = verbose

        # Detect repository type and organization
        try:
            _, self.repo_type, self.org = get_repo_info(self.directory, use_prompt=False)
        except (UserWarning, FileNotFoundError):
            self.repo_type = None
            self.org = "nf-core"  # Default to nf-core if repo info not available

        # Get available modules (local modules for pipelines, repo modules for modules repos)
        self.available_modules = self._get_available_modules()

        # Create a lookup dictionary for quick access by module name
        self.components_by_name = {comp.component_name: comp for comp in self.available_modules}

        # Prompt for module selection if not provided
        # Only allow "all modules" for pipeline repos
        if module is None and not all_modules and len(self.available_modules) > 0:
            allow_all = self.repo_type == "pipeline"
            module = prompt_module_selection(
                self.available_modules, component_type="modules", action="Build containers for", allow_all=allow_all
            )
            # If None returned from prompt, user selected "All modules" (only possible in pipeline repos)
            if module is None:
                all_modules = True

        self.module = module
        self.all_modules = all_modules

        # When a module name is given, use filter_modules_by_name so that a parent folder
        # like "samtools" also selects submodules (samtools/sort, samtools/view, …).
        matched: list[NFCoreComponent] = []
        if module is not None and not self.all_modules and self.available_modules:
            matched = filter_modules_by_name(self.available_modules, module)
            if len(matched) > 1:
                # Prefix match returned several submodules – treat as a filtered "all" run
                self.available_modules = matched
                self.all_modules = True

        # Use NFCoreComponent to handle module directory and file paths
        # For single module mode
        if not self.all_modules:
            # Try exact lookup in the components we already created
            if module is not None and module in self.components_by_name:
                self.nfcore_component: NFCoreComponent | None = self.components_by_name[module]
            elif module is not None and self.available_modules:
                if matched:
                    self.nfcore_component = matched[0]
                else:
                    self.nfcore_component = self._init_nfcore_component(module)
            elif module is not None:
                # Fallback: no available_modules list, create component directly
                self.nfcore_component = self._init_nfcore_component(module)
            else:
                raise ValueError("No module specified and no modules available")

            self.module_directory: Path | None = self.nfcore_component.component_dir
            self.environment_yml: Path | None = self.nfcore_component.environment_yml
            self.meta_yml: Path | None = self.nfcore_component.meta_yml
        else:
            # For all modules mode, these will be set per module during iteration
            self.nfcore_component = None
            self.module_directory = None
            self.environment_yml = None
            self.meta_yml = None

        self.containers: dict | None = None

    @staticmethod
    def check_tower_token() -> None:
        """
        Check if TOWER_ACCESS_TOKEN is set and warn about API limits if not.

        Wave API has rate limits that can be increased by setting the TOWER_ACCESS_TOKEN
        environment variable. This method checks if the token is set and logs a warning
        if it's missing.
        """
        if not os.environ.get("TOWER_ACCESS_TOKEN"):
            log.warning(
                "TOWER_ACCESS_TOKEN is not set. Wave API requests will be subject to stricter rate limits. \n"
                "To increase your quota, set the TOWER_ACCESS_TOKEN environment variable with your Seqera Platform token. \n"
                "See https://docs.seqera.io/wave/api#api-limits for more information."
            )

    def _get_available_modules(self) -> list[NFCoreComponent]:
        """
        Get list of available modules based on repository type.

        For pipeline repos: Returns only local modules (modules/local/)
        For modules repos: Returns modules from the repository
        """
        if not self.repo_type:
            log.debug("Could not determine repository type")
            return []

        if self.repo_type == "pipeline":
            local_modules_dir = self.directory / "modules" / "local"
            return [
                NFCoreComponent(
                    name,
                    None,
                    local_modules_dir / name,
                    self.repo_type,
                    self.directory,
                    "modules",
                    remote_component=False,
                )
                for name in scan_modules_dir(local_modules_dir)
            ]
        elif self.repo_type == "modules":
            return [
                self._init_nfcore_component(name) for name in scan_modules_dir(self.directory / "modules" / self.org)
            ]
        return []

    def _init_nfcore_component(self, module: str) -> NFCoreComponent:
        """Initialize NFCoreComponent for the module."""
        # Construct the correct module directory path
        module_dir = self.directory / "modules" / self.org / module
        return NFCoreComponent(
            component_name=module,
            repo_url="https://github.com/nf-core/modules.git",
            component_dir=module_dir,
            repo_type="modules",
            base_dir=self.directory,
            component_type="modules",
        )

    def cleanup_stale_conda_lock_files(self, new_lock_files: set[Path]) -> None:
        """
        Remove stale conda-lock files that are no longer in the new set.

        Args:
            new_lock_files: Set of new conda lock file paths that should be kept
        """
        if not self.module_directory:
            return

        conda_lock_dir = self.module_directory / ".conda-lock"
        if not conda_lock_dir.exists():
            return

        # Remove all files that aren't in the new set
        for lock_file in conda_lock_dir.glob("*.txt"):
            if lock_file not in new_lock_files:
                try:
                    lock_file.unlink()
                    log.debug(f"Removed stale conda-lock file: {lock_file}")
                except OSError as e:
                    log.warning(f"Failed to remove stale conda-lock file {lock_file}: {e}")

        # Clean up empty directory
        try:
            if not any(conda_lock_dir.iterdir()):
                conda_lock_dir.rmdir()
                log.debug(f"Removed empty .conda-lock directory: {conda_lock_dir}")
        except OSError as e:
            log.debug(f"Could not remove .conda-lock directory: {e}")

    def update_main_nf_container(self, force=False) -> None:
        """Update the container name in main.nf using the docker amd64 image without registry.
        Don't update if the container name is already correct.
        """
        import re

        if not self.containers or not self.nfcore_component:
            log.warning("Cannot update main.nf: containers or nfcore_component not available")
            return

        # Get docker image and strip all path components (registry/path/...)
        linux_amd64 = CONTAINER_PLATFORMS[0]
        docker_image = self.containers.get("docker", {}).get(linux_amd64, {}).get(self.IMAGE_KEY, "")
        if not docker_image:
            log.error(f"No docker image found for {linux_amd64}")
            return

        # Read main.nf
        main_nf_path = self.nfcore_component.main_nf
        content = main_nf_path.read_text()

        # Check if container name is already correct
        if docker_image in content and not force:
            log.info(
                f"Container name in `{self.nfcore_component.component_name}/main.nf` is already correct: `{docker_image}`"
            )
            return

        # Replace container directive (may span multiple lines), preserving indentation
        new_content = re.sub(
            r"(\s*)container\s+\".*?\"", rf'\1container "{docker_image}"', content, count=1, flags=re.DOTALL
        )

        main_nf_path.write_text(new_content)
        log.debug(f"Updated container in `{self.nfcore_component.component_name}/main.nf` to: `{docker_image}`")

    def create(
        self,
        await_build: bool = False,
        progress_bar: rich.progress.Progress | None = None,
        task_id: rich.progress.TaskID | None = None,
        force: bool = False,
    ) -> tuple[dict[str, dict[str, dict[str, str]]], bool]:
        """
        Build docker and singularity containers for linux/amd64 and linux/arm64 using wave.

        Args:
            await_build: Whether to wait for container builds to complete
            progress_bar: Optional progress bar to use for tracking progress
            task_id: Optional task ID for this module in the progress bar

        Returns:
            Tuple of (containers dict, success boolean). Success is False if any build failed.
        """
        # Check for TOWER_ACCESS_TOKEN and warn about API limits
        self.check_tower_token()

        containers: dict = {cs: {p: {} for p in CONTAINER_PLATFORMS} for cs in CONTAINER_SYSTEMS + ["conda"]}
        build_tasks = {}
        threads = max(len(CONTAINER_SYSTEMS) * len(CONTAINER_PLATFORMS), 1)
        has_failures = False

        assert self.environment_yml is not None
        assert self.module_directory is not None

        # One spinner per build target — they run visually in parallel
        build_task_ids: dict[tuple[str, str], rich.progress.TaskID] = {}
        if progress_bar:
            for cs in CONTAINER_SYSTEMS:
                for platform in CONTAINER_PLATFORMS:
                    short_platform = platform.split("/")[-1]
                    build_task_ids[(cs, platform)] = progress_bar.add_task(
                        f"  [dim]{cs}/{short_platform}[/dim]",
                        total=1,
                        completed=0,
                        status="submitting...",
                    )

        def make_on_build_id(cs: str, platform: str) -> Callable[[str], None]:
            def callback(build_id: str) -> None:
                build_tid = build_task_ids.get((cs, platform))
                if progress_bar and build_tid is not None:
                    url = f"https://wave.seqera.io/view/builds/{build_id}"
                    progress_bar.update(build_tid, status=f"building… {url}")

            return callback

        # Submit all container build tasks
        with ThreadPoolExecutor(max_workers=threads) as pool:
            for cs in CONTAINER_SYSTEMS:
                for platform in CONTAINER_PLATFORMS:
                    fut = pool.submit(
                        self.request_container,
                        cs,
                        platform,
                        self.environment_yml,
                        await_build,
                        self.verbose,
                        make_on_build_id(cs, platform) if progress_bar else None,
                    )
                    build_tasks[fut] = (cs, platform)

            # Process completed container builds
            for fut in as_completed(build_tasks):
                cs, platform = build_tasks[fut]
                short_platform = platform.split("/")[-1]
                build_tid = build_task_ids.get((cs, platform))

                try:
                    containers[cs][platform] = fut.result()
                    # Update self.containers and meta.yml after each successful build
                    self.containers = containers
                    try:
                        self.update_containers_in_meta()
                        log.debug(f"Updated meta.yml with {cs} container for {platform}")
                    except (ValueError, RuntimeError, OSError) as meta_error:
                        log.warning(f"Failed to update meta.yml after {cs} {platform} build: {meta_error}")
                    if progress_bar and build_tid is not None:
                        progress_bar.update(build_tid, completed=1, status="[green]done[/green]")
                except (ValueError, RuntimeError, OSError) as e:
                    # make it a warning for arm (not required), but fail for other platforms
                    if platform == "linux/arm64":
                        log.warning(
                            f"Failed to build {cs} container for {platform}: {e}. This is only critical if the tool should support arm64."
                        )
                    else:
                        log.error(f"Failed to build {cs} container for {platform}: {e}")
                        has_failures = True
                    if progress_bar and build_tid is not None:
                        progress_bar.update(build_tid, completed=1, status="[red]failed[/red]")
                    continue

        # Remove the per-build spinners now that all builds are done
        if progress_bar:
            for tid in build_task_ids.values():
                progress_bar.remove_task(tid)

        # Set containers early so get_conda_lock_file can access it
        self.containers = containers

        # Download conda lock files as separate tasks
        new_lock_files = set()
        for platform in CONTAINER_PLATFORMS:
            # Get docker build ID for this platform
            build_id = containers.get("docker", {}).get(platform, {}).get(self.BUILD_ID_KEY, "")
            short_platform = platform.split("/")[-1]
            if not build_id:
                log.debug(f"Docker image for {platform} missing - Conda-lock skipped")
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, status=f"conda lock {short_platform} skipped")
                continue

            conda_lock_path = self.module_directory / ".conda-lock" / f"{platform.replace('/', '_')}-{build_id}.txt"
            conda_lock_path.parent.mkdir(parents=True, exist_ok=True)

            # Store the local file path in containers
            conda_data = containers.get("conda", {})
            conda_data.update({platform: {self.LOCK_FILE_KEY: str(conda_lock_path)}})
            containers["conda"] = conda_data

            try:
                # Download conda lock file (it will look up build_id from docker container)
                log.debug(f"Downloading conda lock file for {platform} to {conda_lock_path}")
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, status=f"conda lock {short_platform}...")
                conda_lock_path.write_text(self.get_conda_lock_file(platform))
                new_lock_files.add(conda_lock_path)
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, status=f"conda lock {short_platform} done")

            except (ValueError, OSError, requests.RequestException) as e:
                log.error(f"Failed to download conda lock file for {platform}: {e}")
                has_failures = True
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, status=f"conda lock {short_platform} failed")

        # Clean up stale conda-lock files
        self.cleanup_stale_conda_lock_files(new_lock_files)

        # Update main.nf with new container name (docker amd64 without registry)
        try:
            self.update_main_nf_container(force)
        except OSError as e:
            log.warning(f"Failed to update main.nf with container name: {e}")
            has_failures = True

        return containers, not has_failures

    @staticmethod
    def _extract_yaml_from_wave_output(output: str) -> str:
        """
        Extract YAML content from Wave CLI output in verbose mode.

        Wave CLI with --log-level DEBUG outputs multi-line DEBUG logs before the YAML response.
        This method finds the first line that looks like YAML (key: value format) and returns
        everything from that point onwards.

        Args:
            output: Raw stdout from Wave CLI

        Returns:
            YAML content with DEBUG lines removed
        """
        lines = output.splitlines()
        for i, line in enumerate(lines):
            # Look for lines that start with a simple word followed by colon (YAML key)
            # Expected keys from Wave: buildId, cached, containerImage, duration, freeze, etc.
            if "DEBUG" not in line and re.match(r"^[a-zA-Z]\w*:\s", line):
                return "\n".join(lines[i:])
        # If no YAML start found, return original output
        return output

    @classmethod
    def request_container(
        cls,
        container_system: str,
        platform: str,
        conda_file: Path,
        await_build=False,
        verbose=False,
        on_build_id: Callable[[str], None] | None = None,
    ) -> dict:
        assert conda_file.exists()
        assert container_system in CONTAINER_SYSTEMS
        assert platform in CONTAINER_PLATFORMS

        container: dict[str, str] = {}
        executable = "wave"
        log_level = "DEBUG" if verbose else "INFO"
        args = [
            "--conda-file",
            str(conda_file.absolute()),
            "--freeze",
            "--platform",
            platform,
            "-o",
            "yaml",
            "--build-template",
            "conda/pixi:v1",
            "--log-level",
            log_level,
        ]
        if container_system == "singularity":
            args.append("--singularity")
        if await_build:
            args.append("--await")

        if on_build_id is not None:
            # Stream stdout line-by-line so we can fire on_build_id as soon as
            # "buildId:" appears in the debug output, without waiting for the build to finish.
            try:
                proc = subprocess.Popen([executable] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError as e:
                raise RuntimeError(
                    f"It looks like {executable} is not installed. Please ensure it is available in your PATH."
                ) from e
            assert proc.stdout and proc.stderr
            stdout_chunks: list[bytes] = []
            build_id_notified = False
            for raw_line in proc.stdout:
                stdout_chunks.append(raw_line)
                if not build_id_notified:
                    m = re.search(rb"buildId:\s*(\S+)", raw_line)
                    if m:
                        on_build_id(m.group(1).decode().strip("\"'"))
                        build_id_notified = True
            stderr_bytes = proc.stderr.read()
            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(
                    f"wave command returned non-zero error code '{proc.returncode}':\n"
                    f"{stderr_bytes.decode()}{b''.join(stdout_chunks).decode()}"
                )
            out: tuple[bytes, bytes] | None = (b"".join(stdout_chunks), stderr_bytes)
        else:
            args_str = " ".join(args)
            out = run_cmd(executable, args_str)

        if out is None:
            raise RuntimeError("Wave command did not return any output")

        # Log stderr when verbose (Wave outputs debug logs there)
        if verbose and out[1]:
            stderr_output = out[1].decode().strip()
            if stderr_output:
                for line in stderr_output.splitlines():
                    log.info(line)

        # Parse Wave output
        stdout_output = out[0].decode()

        # In verbose mode, Wave outputs DEBUG lines before YAML - extract only the YAML part
        if verbose:
            stdout_output = cls._extract_yaml_from_wave_output(stdout_output)

        try:
            meta_data = yaml.safe_load(stdout_output) or {}
            log.debug(f"Wave YAML metadata: \n{pretty_repr(meta_data)}")
        except (KeyError, AttributeError, yaml.YAMLError) as e:
            log.error(f"Failed to parse Wave output. Raw output:\n{stdout_output}")
            raise RuntimeError(f"Could not parse wave YAML metadata ({container_system} {platform})") from e
        if not meta_data.get("succeeded"):
            raise RuntimeError(
                f"Wave build ({container_system} {platform}) failed. Reason: {meta_data.get('reason', 'Unknown')}"
                f"\nBuild log: https://wave.seqera.io/view/builds/{meta_data.get('buildId')}"
                if meta_data.get("buildId")
                else ""
            )
        image = meta_data.get("targetImage") or meta_data.get("containerImage") or ""
        if not image:
            raise RuntimeError(f"Wave build ({container_system} {platform}) did not return an image name")

        container[cls.IMAGE_KEY] = image

        build_id = meta_data.get("buildId", "")
        if build_id:
            container[cls.BUILD_ID_KEY] = build_id

        if container_system == "docker":
            scan_id = meta_data.get("scanId", "")
            if scan_id:
                container[cls.SCAN_ID_KEY] = scan_id

        build_is_done = await_build or meta_data.get("cached", False) or meta_data.get("status") == "DONE"

        if container_system == "singularity" and not build_is_done:
            log.warning(
                "Cannot retrieve https-url by inspecting the image, when the image build is not awaited. Rerun the command with `--await`"
            )

        elif container_system == "singularity":
            inspect_out = cls.request_image_inspect(image)
            container_layers = inspect_out.get("container", {}).get("manifest", {}).get("layers", {})

            if not (
                len(container_layers) == 1
                and container_layers[0].get("mediaType", "").endswith(".sif")
                and container_layers[0].get("digest")
            ):
                log.warning(f"Https-url for image {image} could not be extracted from image inspect output")

            else:
                log.debug(f"Extracting https-uri for {image} from image inspect:\n{pretty_repr(container_layers[0])}")
                digest = container_layers[0]["digest"].replace("sha256:", "")
                container[cls.HTTPS_URL_KEY] = (
                    f"https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/{digest[:2]}/{digest}/data"
                )

        return container

    @classmethod
    def request_image_inspect(cls, image: str) -> dict:
        """
        Request wave container inspect.
        """
        executable = "wave"
        args = ["--inspect", "-o yaml", "-i", image]

        args_str = " ".join(args)
        log.debug(f"Wave command to request image inspect for image {image}: `wave {args_str}`")
        out = run_cmd(executable, args_str)

        if out is None:
            raise RuntimeError("Wave command did not return any output")

        try:
            inspect_out = yaml.safe_load(out[0].decode()) or {}
        except (KeyError, AttributeError, yaml.YAMLError) as e:
            raise RuntimeError(f"Could not parse wave inspect yaml output for image {image}") from e

        return inspect_out

    @staticmethod
    def get_conda_lock_url(build_id) -> str:
        build_id_safe = quote(build_id, safe="")
        url = f"https://wave.seqera.io/v1alpha1/builds/{build_id_safe}/condalock"
        return url

    def get_conda_lock_file(self, platform: str) -> str:
        """
        Get the conda lock file for an existing environment.
        Try (in that order):
            1. reading from meta.yml
            2. reading from cached containers
            3. recreating with wave commands
        """
        assert platform in CONTAINER_PLATFORMS

        containers = self.containers or self.get_containers_from_meta() or self.create()[0] or {}

        # Get build_id from docker container for this platform
        build_id = containers.get("docker", {}).get(platform, {}).get(self.BUILD_ID_KEY)
        if not build_id:
            raise ValueError(f"No build_id found for docker container on platform {platform}")

        # Generate the conda lock URL from the build_id
        conda_lock_url = self.get_conda_lock_url(build_id)

        resp = requests.get(conda_lock_url)
        log.debug(f"Downloading conda lock file from {conda_lock_url}")
        if resp.status_code != 200:
            raise ValueError(f"Failed to download conda lock file from {conda_lock_url}")
        log.debug(f"Successfully downloaded conda lock file from {conda_lock_url}")
        return resp.text

    def list_containers(self) -> list[tuple[str, str, str]]:
        """
        Return containers defined in the module meta.yml as a list of (<container-system>, <platform>, <image-name>).
        """
        containers_valid = self.get_containers_from_meta()
        if not containers_valid:
            return []
        containers_flat = []
        for cs in CONTAINER_SYSTEMS + ["conda"]:
            for p in CONTAINER_PLATFORMS:
                container_entry = containers_valid[cs][p]
                # Add the name entry
                if cs == "conda":
                    containers_flat.append((cs, p, container_entry["lock_file"]))
                else:
                    containers_flat.append((cs, p, container_entry["name"]))
                # For singularity, also add the https entry if available
                if cs == "singularity" and self.HTTPS_URL_KEY in container_entry:
                    containers_flat.append((cs, p, container_entry[self.HTTPS_URL_KEY]))
        return containers_flat

    def get_containers_from_meta(self) -> dict:
        """
        Return containers defined in the module meta.yml.
        Returns empty dict if containers section is missing or incomplete.
        """
        assert self.meta_yml and self.meta_yml.exists()

        meta = read_meta_yml(self.meta_yml)
        containers = meta.get("containers", {})
        if not containers:
            log.debug(f"Section 'containers' missing from meta.yaml for module '{self.module}'")
            return {}

        for system in CONTAINER_SYSTEMS:
            cs = containers.get(system)
            if not cs:
                log.debug(f"Container missing for {system}")
                return {}

            for pf in CONTAINER_PLATFORMS:
                spec = cs.get(pf)
                if not spec:
                    log.debug(f"Platform build {pf} missing for {system} container for module {self.module}")
                    return {}

        return containers

    def update_containers_in_meta(self, module_lint: ModuleLint | None = None) -> None:
        """
        Update the containers section in meta.yml.

        Args:
            module_lint: Optional ModuleLint instance to use for sorting.
                        If not provided, a new instance will be created.
        """
        if self.containers is None:
            log.debug("Containers not initialized - running `create()` ...")
            self.containers, _ = self.create()

        assert self.meta_yml

        meta = read_meta_yml(self.meta_yml)
        meta_containers = meta.get("containers", {})
        # Remove stale entries for platforms that were attempted (even if they failed),
        # so old containers don't mix with new ones when a build partially fails.
        for cs, platforms in self.containers.items():
            for platform in platforms:
                meta_containers.get(cs, {}).pop(platform, None)
        for cs, platforms in self.containers.items():
            for platform, data in platforms.items():
                if data:
                    meta_containers.setdefault(cs, {})[platform] = data
        # Remove empty container system dicts left after clearing stale entries
        meta_containers = {cs: platforms for cs, platforms in meta_containers.items() if platforms}
        meta["containers"] = meta_containers

        # Sort the YAML according to the schema's property order using ModuleLint
        if module_lint is None:
            try:
                module_lint = ModuleLint(self.directory)
            except (UserWarning, ValueError, OSError) as e:
                log.warning(f"Failed to initialize ModuleLint for sorting: {e}")

        if module_lint is not None:
            try:
                meta = module_lint.sort_meta_yml(meta)
            except UserWarning as e:
                log.warning(f"Failed to sort meta.yml: {e}")

        assert self.meta_yml and self.meta_yml.exists()

        with open(self.meta_yml, "w") as f:
            ruamel_yaml.dump(meta, f)

        # Format with prettier for consistent styling
        try:
            run_prettier_on_file(self.meta_yml)
        except (FileNotFoundError, OSError) as e:
            log.debug(f"Could not run prettier on meta.yml: {e}")
