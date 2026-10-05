import base64
import hashlib
import logging
import os
import re
import shutil
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests
import rich.progress
from pydantic import ValidationError
from rich.pretty import pretty_repr

from nf_core.components.components_utils import read_meta_yml
from nf_core.components.components_utils import yaml as ruamel_yaml
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.lint import ModuleLint
from nf_core.modules.modules_utils import (
    CondaEntry,
    ContainerEntry,
    MetaYmlContainers,
    filter_modules_by_name,
    module_uses_dockerfile,
    prompt_module_selection,
    scan_modules_dir,
)
from nf_core.pipelines.lint_utils import run_prettier_on_file
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, ContainerRegistryUrls

log = logging.getLogger(__name__)

WAVE_URL = "https://wave.seqera.io"
WAVE_API_ALPHA1 = f"{WAVE_URL}/v1alpha1"
WAVE_API_ALPHA2 = f"{WAVE_URL}/v1alpha2"

# Wave container build `format` field, keyed by nf-core container system.
WAVE_FORMAT = {"docker": "docker", "singularity": "sif"}


def wave_send(
    method: str, url: str, json_body: dict | None = None, error_context: str = "Wave request"
) -> requests.Response:
    """
    Send an authenticated Wave API request and return the raw response.

    Adds bearer auth (and a ``towerAccessToken`` body field for requests with a body)
    when TOWER_ACCESS_TOKEN is set, and raises on a non-200 response. This is the
    shared transport for all Wave calls; use :func:`wave_request` for JSON endpoints
    and read ``.text`` directly for plain-text ones (e.g. the conda lock file).

    Args:
        method: ``"get"`` or ``"post"``.
        url: Full request URL.
        json_body: Optional JSON body (POST requests).
        error_context: Prefix used in raised error messages.
    """
    if method not in ("get", "post"):
        raise ValueError(f"Invalid http method '{method}' passed. Needs to be one of: 'get', 'post'.")
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("TOWER_ACCESS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
        if json_body is not None:
            json_body = {**json_body, "towerAccessToken": token}

    resp = getattr(requests, method)(url, json=json_body, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"{error_context} failed: HTTP {resp.status_code} {resp.text}")
    return resp


def wave_request(method: str, url: str, json_body: dict | None = None, error_context: str = "Wave request") -> dict:
    """Send a Wave API request and return the parsed JSON response."""
    resp = wave_send(method, url, json_body, error_context)
    try:
        return resp.json()
    except ValueError as e:
        raise RuntimeError(f"{error_context}: could not parse JSON response") from e


class ModuleContainers:
    """
    Helpers for building, linting and listing module containers.
    """

    # Wave build results, keyed by (environment.yml content hash, container_system, platform).
    # Modules with an identical environment.yml (e.g. samtools/sort and samtools/view) resolve
    # to the same container, so this avoids submitting duplicate builds within one process.
    _build_cache: dict[tuple[str, str, str], ContainerEntry] = {}
    # Path to an already-written conda lock file, keyed by Wave build_id. Modules that share
    # a cached build (above) also share a build_id, so a later module can copy the file that
    # an earlier one already downloaded instead of re-fetching identical lock contents.
    _conda_lock_paths: dict[str, Path] = {}
    _build_cache_lock = threading.Lock()

    def __init__(
        self,
        module: str | None,
        directory: str | Path = ".",
        all_modules: bool = False,
        verbose: bool = False,
        components: list[NFCoreComponent] | None = None,
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

        # Get available modules (local modules for pipelines, repo modules for modules repos).
        # A pre-scanned list can be passed in to avoid re-scanning the modules directory.
        self.available_modules = components if components is not None else self._get_available_modules()

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

        self.containers: MetaYmlContainers | None = None
        self._module_lint: ModuleLint | None = None

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

    def _uses_dockerfile(self) -> bool:
        """Return True if the module has a Dockerfile (in its dir or parent) but no environment.yml."""
        if self.nfcore_component is None:
            return False
        return module_uses_dockerfile(self.nfcore_component)

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

        if self._uses_dockerfile():
            log.info(f"Module '{self.module}' uses a Dockerfile - skipping main.nf container update")
            return

        if not self.containers or not self.nfcore_component:
            log.warning("Cannot update main.nf: containers or nfcore_component not available")
            return

        linux_amd64 = CONTAINER_PLATFORMS[0]

        # Get docker image
        _docker_entry = self.containers.docker.get(linux_amd64)
        docker_image = _docker_entry.name if _docker_entry else ""
        if not docker_image:
            log.error(f"No docker image found for {linux_amd64}")
            return

        # Get singularity image, preferring the https download URL over the image name
        _singularity_entry = self.containers.singularity.get(linux_amd64)
        singularity_image = (_singularity_entry.https or _singularity_entry.name) if _singularity_entry else ""
        if not singularity_image:
            log.error(f"No singularity image found for {linux_amd64}")
            return

        # Read main.nf
        main_nf_path = self.nfcore_component.main_nf
        content = main_nf_path.read_text()

        # Check if the container directive is already correct
        if docker_image in content and singularity_image in content and not force:
            log.debug(f"Container directive in `{self.nfcore_component.component_name}/main.nf` is already correct")
            return

        # Replace container directive (may span multiple lines), preserving indentation.
        # The directive uses double quotes on the outside and single quotes inside, so a
        # non-greedy match up to the next double quote captures the whole ternary.
        def _replace(match: "re.Match[str]") -> str:
            indent = match.group(1)
            inner_indent = indent + "    "
            return (
                f"{indent}container \"${{ workflow.containerEngine in ['singularity', 'apptainer'] "
                "&& !task.ext.singularity_pull_docker_container\n"
                f"? {inner_indent}'{singularity_image}'\n"
                f": {inner_indent}'{docker_image}' }}\""
            )

        new_content = re.sub(
            r"^([ \t]*)container\s+\".*?\"", _replace, content, count=1, flags=re.DOTALL | re.MULTILINE
        )

        main_nf_path.write_text(new_content)
        log.debug(
            f"Updated container in `{self.nfcore_component.component_name}/main.nf` "
            f"(docker: `{docker_image}`, singularity: `{singularity_image}`)"
        )

    def create(
        self,
        progress_bar: rich.progress.Progress | None = None,
        task_id: rich.progress.TaskID | None = None,
        force: bool = False,
    ) -> tuple[MetaYmlContainers, bool]:
        """
        Build docker and singularity containers for linux/amd64 and linux/arm64 using wave.

        Args:
            progress_bar: Optional progress bar to use for tracking progress
            task_id: Optional task ID for this module in the progress bar

        Returns:
            Tuple of (MetaYmlContainers, success boolean). Success is False if any build failed.
        """
        containers = MetaYmlContainers()
        build_tasks = {}
        threads = max(len(CONTAINER_SYSTEMS) * len(CONTAINER_PLATFORMS), 1)
        has_failures = False

        if not self.environment_yml:
            if self._uses_dockerfile():
                log.info(f"Module '{self.module}' uses a Dockerfile - skipping Wave container build")
                return MetaYmlContainers(), True
            raise RuntimeError("No environment.yml found.")
        assert self.module_directory is not None

        # One spinner per build target — they run visually in parallel
        build_task_ids: dict[tuple[str, str], rich.progress.TaskID] = {}
        if progress_bar:
            for cs in CONTAINER_SYSTEMS:
                for platform in CONTAINER_PLATFORMS:
                    short_platform = platform.split("/")[-1]
                    build_task_ids[(cs, platform)] = progress_bar.add_task(
                        f"  {cs}/{short_platform}",
                        total=1,
                        completed=0,
                        status="submitting wave build request...",
                    )

        def make_on_build_id(cs: str, platform: str) -> Callable[[str], None]:
            def callback(build_id: str) -> None:
                build_tid = build_task_ids.get((cs, platform))
                if progress_bar and build_tid is not None:
                    url = f"{WAVE_URL}/view/builds/{build_id}"
                    progress_bar.update(build_tid, status=f"building… {url}")

            return callback

        # Set by the main thread on Ctrl+C so in-flight build waiters abort promptly
        # instead of sleeping out their poll interval / full build timeout.
        cancel_event = threading.Event()

        # Submit all container build tasks
        with ThreadPoolExecutor(max_workers=threads) as pool:
            for cs in CONTAINER_SYSTEMS:
                for platform in CONTAINER_PLATFORMS:
                    fut = pool.submit(
                        self.request_container,
                        cs,
                        platform,
                        self.environment_yml,
                        self.verbose,
                        make_on_build_id(cs, platform) if progress_bar else None,
                        cancel_event,
                    )
                    build_tasks[fut] = (cs, platform)

            # Process completed container builds
            try:
                for fut in as_completed(build_tasks):
                    cs, platform = build_tasks[fut]
                    short_platform = platform.split("/")[-1]
                    build_tid = build_task_ids.get((cs, platform))

                    try:
                        getattr(containers, cs)[platform] = fut.result()
                        if progress_bar and build_tid is not None:
                            progress_bar.update(build_tid, completed=1, status="[green]done[/green]")
                    except (ValueError, RuntimeError, OSError, AssertionError) as e:
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
            except KeyboardInterrupt:
                # Signal the running build waiters to stop, drop anything not yet started,
                # and re-raise so the command aborts instead of blocking on the executor's
                # wait-for-all shutdown.
                log.warning("Interrupted — cancelling Wave builds...")
                cancel_event.set()
                pool.shutdown(wait=False, cancel_futures=True)
                raise

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
            _docker_entry = containers.docker.get(platform)
            build_id = _docker_entry.build_id if _docker_entry else ""
            short_platform = platform.split("/")[-1]
            if not build_id:
                log.debug(f"Docker image for {platform} missing - Conda-lock skipped")
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, status=f"conda lock {short_platform} skipped")
                continue

            conda_lock_path = self.module_directory / ".conda-lock" / f"{platform.replace('/', '_')}-{build_id}.txt"
            conda_lock_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with self._build_cache_lock:
                    cached_lock_path = self._conda_lock_paths.get(build_id)
                if cached_lock_path is not None and cached_lock_path.exists():
                    log.debug(f"Reusing conda lock file for build {build_id} (from {cached_lock_path})")
                    if progress_bar and task_id is not None:
                        progress_bar.update(task_id, status=f"conda lock {short_platform} (cached)...")
                    if cached_lock_path != conda_lock_path:
                        shutil.copyfile(cached_lock_path, conda_lock_path)
                else:
                    # Download conda lock file (it will look up build_id from docker container)
                    log.debug(f"Downloading conda lock file for {platform} to {conda_lock_path}")
                    if progress_bar and task_id is not None:
                        progress_bar.update(task_id, status=f"conda lock {short_platform}...")
                    conda_lock_path.write_text(self.get_conda_lock_file(platform))
                    with self._build_cache_lock:
                        self._conda_lock_paths[build_id] = conda_lock_path
                # Only register the entry once the lock has actually been written, so
                # meta.yml never points at a missing lock file.
                containers.conda[platform] = CondaEntry(lock_file=str(conda_lock_path))
                new_lock_files.add(conda_lock_path)
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, status=f"conda lock {short_platform} done")

            except (ValueError, RuntimeError, OSError, requests.RequestException) as e:
                # Wave does not always expose a conda lock for every build (e.g. some
                # freshly built arm64 images). A missing lock is not fatal: keep the
                # other platforms' containers and locks instead of failing the module.
                log.warning(f"No conda lock file available for {platform}: {e}")
                if progress_bar and task_id is not None:
                    progress_bar.update(task_id, status=f"conda lock {short_platform} unavailable")

        # Clean up stale conda-lock files
        self.cleanup_stale_conda_lock_files(new_lock_files)

        # Persist everything (docker, singularity and conda locks) to meta.yml in a
        # single write. Partial results are kept even if some builds failed.
        if any(getattr(containers, cs) for cs in CONTAINER_SYSTEMS + ["conda"]):
            try:
                self.update_containers_in_meta()
                log.debug("Updated meta.yml with built containers")
            except (ValueError, RuntimeError, OSError) as meta_error:
                log.warning(f"Failed to update meta.yml after container builds: {meta_error}")

        # Update main.nf with new container name (docker amd64 without registry)
        try:
            self.update_main_nf_container(force)
        except OSError as e:
            log.warning(f"Failed to update main.nf with container name: {e}")
            has_failures = True

        return containers, not has_failures

    @staticmethod
    def _raise_if_build_failed(result: dict, build_ref: str, details_uri: str = "") -> None:
        """
        Raise a uniform error if a finished Wave build did not succeed.

        Accepts either the container submit response or a ``/status`` response — both
        expose ``succeeded``/``reason``/``detailsUri`` — so the failure contract lives
        in one place. ``details_uri`` overrides the value on ``result`` (the status
        poller keeps the last non-empty build-log URL it saw).
        """
        if result.get("succeeded"):
            return
        reason = result.get("reason") or "no reason provided"
        details = details_uri or result.get("detailsUri") or ""
        raise RuntimeError(f"Wave build {build_ref} failed: {reason}. Build log: {details}")

    def build_containers_with_progress(self, force: bool = False, hide_progress: bool = False) -> list[str]:
        """Build Seqera/Wave containers for the selected module(s) with a live progress display.

        Builds the single selected module, or every module in ``available_modules`` when
        the instance was created with ``all_modules=True``. Shows an overall module bar
        plus, per module, the per-build spinners (docker/singularity × platform) that
        :meth:`create` renders when a progress bar is passed.

        Args:
            force: Overwrite existing container directives even if already correct.
            hide_progress: Disable the live progress display.

        Returns:
            The names of the modules whose builds failed.
        """
        from rich.console import Group
        from rich.live import Live
        from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn

        from nf_core.pipelines.containers_utils import try_generate_container_configs
        from nf_core.pipelines.lint_utils import console

        if self.all_modules:
            components = self.available_modules
        else:
            assert self.nfcore_component is not None
            components = [self.nfcore_component]

        failed_modules: list[str] = []

        overall_progress = Progress(
            "[bold blue]{task.description}",
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
            disable=hide_progress,
        )
        module_progress = Progress(
            SpinnerColumn(finished_text="[green]✓[/green]"),
            "[bold blue]{task.description}",
            TextColumn("{task.fields[status]}"),
            console=console,
            disable=hide_progress,
        )

        # Batch builds defer config generation to one full scan after the loop.
        batch = len(components) > 1

        with Live(Group(overall_progress, module_progress), console=console, transient=True):
            # The overall bar is only useful when processing more than one module
            overall_task_id = overall_progress.add_task("modules", total=len(components), visible=len(components) > 1)
            for component in components:
                module_name = component.component_name
                module_task_id = module_progress.add_task(
                    f"[cyan]{module_name}[/cyan]",
                    total=None,
                    status="building containers...",
                )
                try:
                    if self.all_modules:
                        # Per-module instance, reusing the already-scanned component list
                        module_containers = ModuleContainers(
                            module=module_name,
                            directory=self.directory,
                            verbose=self.verbose,
                            components=self.available_modules,
                        )
                    else:
                        module_containers = self
                    _, success = module_containers.create(
                        progress_bar=module_progress, task_id=module_task_id, force=force
                    )
                    if success:
                        if module_containers.repo_type == "pipeline" and not batch:
                            try_generate_container_configs(self.directory, module_containers.module_directory)
                    else:
                        failed_modules.append(module_name)
                except (ValueError, RuntimeError, OSError) as e:
                    log.error(f"✗ Failed to build containers for {module_name}: {e}")
                    failed_modules.append(module_name)
                finally:
                    overall_progress.advance(overall_task_id)
                    module_progress.remove_task(module_task_id)

        if batch and self.repo_type == "pipeline" and len(failed_modules) < len(components):
            try_generate_container_configs(self.directory)

        return failed_modules

    @classmethod
    def _await_build(
        cls,
        request_id: str,
        poll_interval: int = 5,
        timeout: int = 1800,
        cancel_event: threading.Event | None = None,
    ) -> None:
        """
        Wait for a Wave container request to finish by polling its status endpoint.

        Replaces the wave CLI ``--await`` flag. Polls ``GET /v1alpha2/container/{id}/status``
        until the request reports ``DONE``, then raises (with the failure ``reason``) if it
        did not succeed.

        Args:
            request_id: The Wave request id returned by the container submit request.
            poll_interval: Seconds to wait between status checks.
            timeout: Maximum seconds to wait before giving up.
            cancel_event: When set (by the main thread on Ctrl+C), abort the wait promptly
                instead of sleeping out the poll interval.
        """
        if not request_id:
            raise RuntimeError("Wave did not return a requestId to await")

        status_url = f"{WAVE_API_ALPHA2}/container/{quote(request_id, safe='')}/status"
        # Updated from each status response; the API returns a ready-made build log URL.
        details_uri = ""
        deadline = time.monotonic() + timeout
        while True:
            if cancel_event is not None and cancel_event.is_set():
                raise RuntimeError(f"Wave build {request_id} await cancelled")
            status = wave_request("get", status_url, error_context=f"Wave status check for request {request_id}")
            details_uri = status.get("detailsUri") or details_uri
            if status.get("status") == "DONE":
                cls._raise_if_build_failed(status, request_id, details_uri)
                log.debug(f"Wave build {request_id} completed in {status.get('duration')}s")
                return
            if time.monotonic() > deadline:
                raise RuntimeError(
                    f"Wave build {request_id} did not complete within {timeout}s. Build log: {details_uri}"
                )
            # Interruptible sleep: Event.wait returns True immediately once cancelled,
            # otherwise blocks for poll_interval like time.sleep.
            if cancel_event is not None:
                if cancel_event.wait(poll_interval):
                    raise RuntimeError(f"Wave build {request_id} await cancelled")
            else:
                time.sleep(poll_interval)

    @classmethod
    def request_container(
        cls,
        container_system: str,
        platform: str,
        conda_file: Path,
        verbose=False,
        on_build_id: Callable[[str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> ContainerEntry:
        assert conda_file.exists()
        assert container_system in CONTAINER_SYSTEMS
        assert platform in CONTAINER_PLATFORMS

        conda_bytes = conda_file.read_bytes()
        cache_key = (hashlib.sha256(conda_bytes).hexdigest(), container_system, platform)
        with cls._build_cache_lock:
            cached_entry = cls._build_cache.get(cache_key)
        if cached_entry is not None:
            log.debug(f"Reusing cached {container_system}/{platform} build for identical environment.yml")
            return cached_entry

        # Submit the build via the Wave HTTP API (POST /v1alpha2/container).
        # `freeze` with no buildRepository pushes to the public community registry.
        payload: dict = {
            "packages": {
                "type": "CONDA",
                "environment": base64.b64encode(conda_bytes).decode(),
            },
            "containerPlatform": platform,
            "freeze": True,
            "buildTemplate": "conda/pixi:v1",
            "basePackages": "conda-forge::procps conda-forge::gzip",
            "format": WAVE_FORMAT[container_system],
            "nameStrategy": "imageSuffix",
        }
        meta_data = wave_request(
            "post",
            f"{WAVE_API_ALPHA2}/container",
            payload,
            error_context=f"Wave build submit ({container_system} {platform})",
        )
        log.log(
            logging.INFO if verbose else logging.DEBUG,
            f"Wave response ({container_system} {platform}):\n{pretty_repr(meta_data)}",
        )

        build_id = meta_data.get("buildId") or ""
        request_id = meta_data.get("requestId") or ""
        # Notify as soon as we have a build id, before waiting for the build to finish.
        if build_id and on_build_id is not None:
            on_build_id(build_id)

        # Wave returns a targetImage/buildId even for failed builds, so a cached/DONE
        # submit response must still be checked for success — not only the polling path.
        succeeded = meta_data.get("succeeded")
        is_final = bool(meta_data.get("cached")) or meta_data.get("status") == "DONE"
        if is_final and succeeded is not None:
            # Submit response already carries an authoritative result.
            cls._raise_if_build_failed(meta_data, build_id or request_id)
        elif not is_final or request_id:
            # Not final, or final but ambiguous: the status endpoint is authoritative.
            cls._await_build(request_id, cancel_event=cancel_event)

        image = meta_data.get("targetImage") or meta_data.get("containerImage") or ""
        if not image:
            raise RuntimeError(f"Wave build ({container_system} {platform}) did not return an image name")

        scan_id = ""
        https_url = ""

        if container_system == "docker":
            scan_id = meta_data.get("scanId") or ""

        if container_system == "singularity":
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
                https_url = (
                    f"https://{ContainerRegistryUrls.SEQERA_SINGULARITY.value}/blobs/sha256/{digest[:2]}/{digest}/data"
                )

        entry = ContainerEntry(name=image, build_id=build_id, scan_id=scan_id, https=https_url)
        with cls._build_cache_lock:
            cls._build_cache[cache_key] = entry
        return entry

    @classmethod
    def request_image_inspect(cls, image: str) -> dict:
        """
        Inspect a container image via the Wave HTTP API (POST /v1alpha1/inspect).
        """
        log.debug(f"Requesting Wave image inspect for image {image}")
        return wave_request(
            "post",
            f"{WAVE_API_ALPHA1}/inspect",
            {"containerImage": image},
            error_context=f"Wave inspect for image {image}",
        )

    @staticmethod
    def get_conda_lock_url(build_id) -> str:
        build_id_safe = quote(build_id, safe="")
        url = f"{WAVE_API_ALPHA1}/builds/{build_id_safe}/condalock"
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

        containers = self.containers or self.get_containers_from_meta() or self.create()[0]

        # Get build_id from docker container for this platform
        _docker_entry = containers.docker.get(platform) if containers else None
        build_id = _docker_entry.build_id if _docker_entry else None
        if not build_id:
            raise ValueError(f"No build_id found for docker container on platform {platform}")

        # Generate the conda lock URL from the build_id
        conda_lock_url = self.get_conda_lock_url(build_id)

        # condalock returns plain text; route through the shared transport so the download
        # shares Wave auth (and thus the relaxed rate limits) with the other Wave calls.
        log.debug(f"Downloading conda lock file from {conda_lock_url}")
        resp = wave_send("get", conda_lock_url, error_context=f"Conda lock download for platform {platform}")
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
                if cs == "conda":
                    conda_entry = containers_valid.conda.get(p)
                    if conda_entry:
                        containers_flat.append((cs, p, conda_entry.lock_file))
                else:
                    entry = getattr(containers_valid, cs).get(p)
                    if entry:
                        containers_flat.append((cs, p, entry.name))
                        if cs == "singularity" and entry.https:
                            containers_flat.append((cs, p, entry.https))
        return containers_flat

    def get_containers_from_meta(self) -> MetaYmlContainers | None:
        """
        Return containers defined in the module meta.yml.
        Returns None if containers section is missing, incomplete, or invalid.
        """
        if self.meta_yml is None or not self.meta_yml.exists():
            raise FileNotFoundError(f"No meta.yml found for module '{self.module}'")

        meta = read_meta_yml(self.meta_yml)
        containers = meta.get("containers", {})
        if not containers:
            log.debug(f"Section 'containers' missing from meta.yaml for module '{self.module}'")
            return None

        try:
            return MetaYmlContainers.model_validate(containers, context={"require_complete": True})
        except ValidationError as e:
            log.debug(f"Could not parse containers from meta.yml: {e}")
            return None

    def update_containers_in_meta(self, module_lint: ModuleLint | None = None) -> None:
        """
        Update the containers section in meta.yml.

        Args:
            module_lint: Optional ModuleLint instance to use for sorting.
                        If not provided, a new instance will be created.
        """
        if self._uses_dockerfile():
            log.info(f"Module '{self.module}' uses a Dockerfile - skipping meta.yml container update")
            return

        if self.containers is None:
            log.debug("Containers not initialized - running `create()` ...")
            self.containers, _ = self.create()

        if self.meta_yml is None or not self.meta_yml.exists():
            raise FileNotFoundError(f"No meta.yml found for module '{self.module}'")

        meta = read_meta_yml(self.meta_yml)
        meta_containers = meta.get("containers", {})
        # Remove stale entries for all known systems/platforms so old containers don't
        # mix with new ones when a build partially fails.
        for cs in CONTAINER_SYSTEMS + ["conda"]:
            for platform in CONTAINER_PLATFORMS:
                meta_containers.get(cs, {}).pop(platform, None)
        new_containers = self.containers.dump_for_meta_yml()
        for cs, platforms in new_containers.items():
            for platform, data in platforms.items():
                if data:
                    meta_containers.setdefault(cs, {})[platform] = data
        # Remove empty container system dicts left after clearing stale entries
        meta_containers = {cs: platforms for cs, platforms in meta_containers.items() if platforms}
        meta["containers"] = meta_containers

        # Sort the YAML according to the schema's property order using ModuleLint
        # (constructed once per instance - it re-scans the modules repo)
        if module_lint is None:
            if self._module_lint is None:
                try:
                    self._module_lint = ModuleLint(self.directory)
                except (UserWarning, ValueError, OSError) as e:
                    log.warning(f"Failed to initialize ModuleLint for sorting: {e}")
            module_lint = self._module_lint

        if module_lint is not None:
            try:
                meta = module_lint.sort_meta_yml(meta)
            except UserWarning as e:
                log.warning(f"Failed to sort meta.yml: {e}")

        with open(self.meta_yml, "w") as f:
            ruamel_yaml.dump(meta, f)

        # Format with prettier for consistent styling
        try:
            run_prettier_on_file(self.meta_yml)
        except (FileNotFoundError, OSError) as e:
            log.debug(f"Could not run prettier on meta.yml: {e}")
