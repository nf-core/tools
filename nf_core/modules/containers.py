import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests
import rich.progress
import yaml

from nf_core.components.components_utils import yaml as ruamel_yaml
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.lint import ModuleLint
from nf_core.modules.modules_utils import prompt_module_selection
from nf_core.pipelines.lint_utils import run_prettier_on_file
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, run_cmd

log = logging.getLogger(__name__)


class ModuleContainers:
    """
    Helpers for building, linting and listing module containers.
    """

    IMAGE_KEY = "name"
    BUILD_ID_KEY = "buildId"
    SCAN_ID_KEY = "scanId"
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

        # Use NFCoreComponent to handle module directory and file paths
        # For single module mode
        if not self.all_modules:
            # First try to find it in the components we already created
            if module is not None and module in self.components_by_name:
                self.nfcore_component: NFCoreComponent | None = self.components_by_name[module]
            elif module is not None:
                # Fallback to creating a new one (for when module name is provided directly)
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

        modules = []

        if self.repo_type == "pipeline":
            # For pipelines, only return local modules
            local_modules_dir = self.directory / "modules" / "local"
            if local_modules_dir.exists():
                seen_modules = set()
                # Handle directories with main.nf files
                for main_nf in local_modules_dir.rglob("main.nf"):
                    # Skip if this main.nf is directly in local_modules_dir
                    # (would be an unusual structure)
                    if main_nf.parent == local_modules_dir:
                        continue
                    module_name = str(main_nf.parent.relative_to(local_modules_dir))
                    # Only include if we haven't seen this module before (avoid duplicates from nested main.nf)
                    if module_name not in seen_modules:
                        seen_modules.add(module_name)
                        modules.append(
                            NFCoreComponent(
                                module_name,
                                None,
                                main_nf.parent,
                                self.repo_type,
                                self.directory,
                                "modules",
                                remote_component=False,
                            )
                        )

        elif self.repo_type == "modules":
            # For modules repos, get modules from modules directory
            modules_dir = self.directory / "modules" / self.org
            if modules_dir.exists():
                seen_modules = set()
                for main_nf in modules_dir.rglob("main.nf"):
                    module_name = str(main_nf.parent.relative_to(modules_dir))
                    # Only include if we haven't seen this module before (avoid duplicates from nested main.nf)
                    if module_name not in seen_modules:
                        seen_modules.add(module_name)
                        modules.append(self._init_nfcore_component(module_name))

        return modules

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
                except Exception as e:
                    log.warning(f"Failed to remove stale conda-lock file {lock_file}: {e}")

        # Clean up empty directory
        try:
            if not any(conda_lock_dir.iterdir()):
                conda_lock_dir.rmdir()
                log.debug(f"Removed empty .conda-lock directory: {conda_lock_dir}")
        except Exception as e:
            log.debug(f"Could not remove .conda-lock directory: {e}")

    def update_main_nf_container(self) -> None:
        """Update the container name in main.nf using the docker amd64 image without registry."""
        import re

        if not self.containers or not self.nfcore_component:
            log.warning("Cannot update main.nf: containers or nfcore_component not available")
            return

        # Get docker image and strip all path components (registry/path/...)
        docker_image = self.containers.get("docker", {}).get("linux/amd64", {}).get(self.IMAGE_KEY, "")
        if not docker_image:
            log.warning("No docker image found for linux/amd64")
            return

        # Get just the image:tag (last component after /)
        # e.g., "community.wave.seqera.io/library/image:tag" -> "image:tag"
        container_name = docker_image.split("/")[-1]

        # Update main.nf
        main_nf_path = self.nfcore_component.main_nf
        content = main_nf_path.read_text()

        # Replace container directive, preserving indentation
        new_content = re.sub(r"(\s*)container\s+.*", rf'\1container "{container_name}"', content, count=1)

        main_nf_path.write_text(new_content)
        log.info(f"Updated container in {main_nf_path} to: {container_name}")

    def create(
        self, await_build: bool = False, progress_bar: rich.progress.Progress | None = None, task_id: int | None = None
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

        containers: dict = {cs: {p: dict() for p in CONTAINER_PLATFORMS} for cs in CONTAINER_SYSTEMS + ["conda"]}
        build_tasks = dict()
        threads = max(len(CONTAINER_SYSTEMS) * len(CONTAINER_PLATFORMS), 1)
        has_failures = False

        assert self.environment_yml is not None
        assert self.module_directory is not None

        # Submit all container build tasks
        with ThreadPoolExecutor(max_workers=threads) as pool:
            for cs in CONTAINER_SYSTEMS:
                for platform in CONTAINER_PLATFORMS:
                    fut = pool.submit(
                        self.request_container, cs, platform, self.environment_yml, await_build, self.verbose
                    )
                    build_tasks[fut] = (cs, platform)

            # Process completed container builds
            for fut in as_completed(build_tasks):
                cs, platform = build_tasks[fut]

                # Try to get the result, but continue on failure
                try:
                    containers[cs][platform] = fut.result()
                    if progress_bar and task_id is not None:
                        progress_bar.update(task_id, advance=1)
                except Exception as e:
                    log.error(f"Failed to build {cs} container for {platform}: {e}")
                    has_failures = True
                    if progress_bar and task_id is not None:
                        progress_bar.update(task_id, advance=1)
                    continue

        # Download conda lock files as separate tasks
        new_lock_files = set()
        for platform in CONTAINER_PLATFORMS:
            # Get docker build ID for this platform
            build_id = containers.get("docker", {}).get(platform, {}).get(self.BUILD_ID_KEY, "")
            if not build_id:
                log.debug(f"Docker image for {platform} missing - Conda-lock skipped")
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, advance=1)
                continue

            platform_safe = platform.replace("/", "-")
            conda_data = containers.get("conda", dict())
            conda_lock_path = self.module_directory / ".conda-lock" / f"{platform_safe}-{build_id}.txt"
            conda_lock_path.parent.mkdir(parents=True, exist_ok=True)
            conda_data.update({platform: {self.LOCK_FILE_KEY: str(conda_lock_path)}})
            containers["conda"] = conda_data

            try:
                conda_lock_url = self.get_conda_lock_url(build_id)
                # Download conda lock file
                log.debug(f"Downloading conda lock file for {platform} from {conda_lock_url} to {conda_lock_path}")
                conda_lock_path.write_text(self.request_conda_lock_file(conda_lock_url))
                new_lock_files.add(conda_lock_path)
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, advance=1)

            except Exception as e:
                log.error(f"Failed to download conda lock file for {platform}: {e}")
                has_failures = True
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, advance=1)

        # Clean up stale conda-lock files
        self.cleanup_stale_conda_lock_files(new_lock_files)

        self.containers = containers

        # Update main.nf with new container name (docker amd64 without registry)
        try:
            self.update_main_nf_container()
        except Exception as e:
            log.warning(f"Failed to update main.nf with container name: {e}")
            has_failures = True

        return containers, not has_failures

    @classmethod
    def request_container(
        cls, container_system: str, platform: str, conda_file: Path, await_build=False, verbose=False
    ) -> dict:
        assert conda_file.exists()
        assert container_system in CONTAINER_SYSTEMS
        assert platform in CONTAINER_PLATFORMS

        container: dict[str, str] = dict()
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

        try:
            meta_data = yaml.safe_load(out[0].decode()) or dict()
            log.debug(f"Wave YAML metadata: {meta_data}")
        except (KeyError, AttributeError, yaml.YAMLError) as e:
            log.error(f"Failed to parse Wave output. Raw output:\n{out[0].decode()}")
            raise RuntimeError(f"Could not parse wave YAML metadata ({container_system} {platform})") from e
        if not meta_data.get("succeeded"):
            raise RuntimeError(
                f"Wave build ({container_system} {platform}) failed. Reason: {meta_data.get('reason', 'Unknown')}"
                f"\nBuild log: https://wave.seqera.io/view/builds/{meta_data.get(cls.BUILD_ID_KEY)}"
                if meta_data.get(cls.BUILD_ID_KEY)
                else ""
            )
        image = meta_data.get("targetImage") or meta_data.get("containerImage") or ""
        if not image:
            raise RuntimeError(f"Wave build ({container_system} {platform}) did not return an image name")

        container[cls.IMAGE_KEY] = image

        build_id = meta_data.get(cls.BUILD_ID_KEY, "")
        if build_id:
            container[cls.BUILD_ID_KEY] = build_id

        if container_system == "docker":
            scan_id = meta_data.get(cls.SCAN_ID_KEY, "")
            if scan_id:
                container[cls.SCAN_ID_KEY] = scan_id

        if container_system == "singularity" and not await_build:
            log.warning(
                "Cannot retrieve https-url by inspecting the image, when the image build is not awaited. Rerun the command with `--await`"
            )

        elif container_system == "singularity":
            inspect_out = cls.request_image_inspect(image)
            container_layers = inspect_out.get("container", dict()).get("manifest", dict()).get("layers", dict())

            if not (
                len(container_layers) == 1
                and container_layers[0].get("mediaType", "").endswith(".sif")
                and container_layers[0].get("digest")
            ):
                log.warning(f"Https-url for image {image} could not be extracted from image inspect output")

            else:
                log.debug(f"Extracting https-uri for {image} from image inspect: {container_layers[0]}")
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
            inspect_out = yaml.safe_load(out[0].decode()) or dict()
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

        containers = self.containers or self.get_containers_from_meta() or self.create()[0] or dict()

        conda_lock_url = containers.get("conda", dict()).get(platform, dict()).get(self.LOCK_FILE_KEY)
        if not conda_lock_url:
            raise ValueError("No conda lock file found")

        return self.request_conda_lock_file(conda_lock_url)

    @staticmethod
    def request_conda_lock_file(conda_lock_url: str) -> str:
        resp = requests.get(conda_lock_url)
        log.debug(f"Downloading conda lock file from {conda_lock_url}")
        if resp.status_code != 200:
            raise ValueError(f"Failed to download conda lock file from {conda_lock_url}")
        log.debug(f"Successfully downloaded conda lock file from {conda_lock_url}")
        return resp.text

    # def lint(self, module: str) -> list[str]:
    #     """
    #     Confirm containers are defined for the module.
    #     """
    #     return self._containers_from_meta(self._resolve_module_dir(module))

    def list_containers(self) -> list[tuple[str, str, str]]:
        """
        Return containers defined in the module meta.yml as a list of (<container-system>, <platform>, <image-name>).
        """
        containers_valid = self.get_containers_from_meta()
        containers_flat = [
            (cs, p, containers_valid[cs][p]["name"]) for cs in CONTAINER_SYSTEMS for p in CONTAINER_PLATFORMS
        ]
        return containers_flat

    def get_meta(self) -> dict:
        """Load and return the meta.yml content."""
        if not self.meta_yml or not self.meta_yml.exists():
            raise FileNotFoundError(f"meta.yml not found for module '{self.module}'")
        with open(self.meta_yml) as f:
            meta = ruamel_yaml.load(f)
        return meta

    def get_containers_from_meta(self) -> dict:
        """
        Return containers defined in the module meta.yml.
        Returns empty dict if containers section is missing or incomplete.
        """
        assert self.meta_yml and self.meta_yml.exists()

        meta = self.get_meta()
        containers = meta.get("containers", dict())
        if not containers:
            log.debug(f"Section 'containers' missing from meta.yaml for module '{self.module}'")
            return dict()

        for system in CONTAINER_SYSTEMS:
            cs = containers.get(system)
            if not cs:
                log.debug(f"Container missing for {system}")
                return dict()

            for pf in CONTAINER_PLATFORMS:
                spec = containers.get(pf)
                if not spec:
                    log.debug(f"Platform build {pf} missing for {system} container for module {self.module}")
                    return dict()

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
            self.create()[0]  # Ignore success status, just get containers

        meta = self.get_meta()
        meta_containers = meta.get("containers", dict())
        meta_containers.update(self.containers)
        meta["containers"] = meta_containers

        # Sort the YAML according to the schema's property order using ModuleLint
        if module_lint is None:
            try:
                module_lint = ModuleLint(self.directory)
            except Exception as e:
                log.warning(f"Failed to initialize ModuleLint for sorting: {e}")

        if module_lint is not None:
            try:
                meta = module_lint.sort_meta_yml(meta)
            except Exception as e:
                log.warning(f"Failed to sort meta.yml: {e}")

        assert self.meta_yml and self.meta_yml.exists()

        with open(self.meta_yml, "w") as f:
            ruamel_yaml.dump(meta, f)

        # Format with prettier for consistent styling
        try:
            run_prettier_on_file(self.meta_yml)
        except Exception as e:
            log.debug(f"Could not run prettier on meta.yml: {e}")
