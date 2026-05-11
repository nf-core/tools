import contextlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from nf_core.utils import read_module_name

log = logging.getLogger(__name__)

PLATFORMS: dict[str, list[str]] = {
    "docker_amd64": ["docker", "linux/amd64", "name"],
    "docker_arm64": ["docker", "linux/arm64", "name"],
    "singularity_oras_amd64": ["singularity", "linux/amd64", "name"],
    "singularity_oras_arm64": ["singularity", "linux/arm64", "name"],
    "singularity_https_amd64": ["singularity", "linux/amd64", "https"],
    "singularity_https_arm64": ["singularity", "linux/arm64", "https"],
    "conda_lock_files_amd64": ["conda", "linux/amd64", "lock_file"],
    "conda_lock_files_arm64": ["conda", "linux/arm64", "lock_file"],
}

_CONFIG_LINE_RE = re.compile(r"withName:\s*'(\w+)'\s*\{\s*(?:container|conda)\s*=\s*'([^']+)'")


def _container_key(platform: str) -> str:
    return "conda" if platform.startswith("conda_lock_") else "container"


def _parse_config_file(config_path: Path) -> dict[str, str]:
    """Return {module_name: container} from an existing platform config file."""
    result: dict[str, str] = {}
    with contextlib.suppress(OSError):
        for line in config_path.read_text().splitlines():
            m = _CONFIG_LINE_RE.search(line)
            if m:
                result[m.group(1)] = m.group(2)
    return result


def _write_platform_config(config_path: Path, entries: dict[str, str], key: str) -> bool:
    """Write *entries* to *config_path*, or delete it when empty.

    Skips the write when content is unchanged.  Returns True if the file now exists.
    """
    if not entries:
        config_path.unlink(missing_ok=True)
        return False
    new_content = "".join(
        f"process {{ withName: '{name}' {{ {key} = '{container}' }} }}\n" for name, container in sorted(entries.items())
    )
    if not config_path.exists() or config_path.read_text() != new_content:
        config_path.write_text(new_content)
    return True


def _process_meta(meta_path: Path) -> tuple[str, dict[str, str]] | None:
    """Read one meta.yml + sibling main.nf and return (module_name, {platform: container}).

    Returns None when the file should be skipped.
    """
    try:
        raw = meta_path.read_bytes()
    except OSError as e:
        log.debug(f"Could not read {meta_path}: {e}")
        return None

    # TODO: remove this early-exit once containers are present in the majority of modules
    if b"containers:" not in raw:
        return None

    meta = yaml.safe_load(raw)

    module_name = read_module_name(meta_path.parent / "main.nf")
    if not module_name:
        log.debug(f"No process definition found next to {meta_path}, skipping")
        return None

    platform_containers: dict[str, str] = {}
    for platform_name, (runtime, arch, protocol) in PLATFORMS.items():
        with contextlib.suppress(KeyError, TypeError):
            platform_containers[platform_name] = meta["containers"][runtime][arch][protocol]

    return module_name, platform_containers


class ContainerConfigs:
    """Generates the container configuration files for a pipeline.

    Args:
        workflow_directory (Path): The directory containing the workflow files.
    """

    def __init__(self, workflow_directory: Path = Path()) -> None:
        self.workflow_directory = workflow_directory

    def update_module_container_config(self, module_path: Path) -> None:
        """Targeted update for a single module.

        Reads the current config files, splices in (or removes) the entry for
        the module at *module_path*, and writes back only what changed.
        """
        result = _process_meta(module_path / "meta.yml")

        if result is None:
            module_name = read_module_name(module_path / "main.nf")
            if not module_name:
                log.debug(f"Could not determine process name for {module_path}, skipping")
                return
            platform_containers: dict[str, str] = {}
        else:
            module_name, platform_containers = result

        conf_dir = self.workflow_directory / "conf"
        for platform in PLATFORMS:
            config_path = conf_dir / f"containers_{platform}.config"
            entries = _parse_config_file(config_path)
            if platform in platform_containers:
                entries[module_name] = platform_containers[platform]
            _write_platform_config(config_path, entries, _container_key(platform))

    def generate_container_configs(self) -> set[str]:
        """Full scan of all ``meta.yml`` files under ``modules/``.

        Used by lint and bulk operations (update, remove, patch) where multiple
        modules may have changed.

        Returns:
            set[str]: Names of config files written (e.g. ``{'containers_docker_amd64.config'}``).
        """
        modules_dir = self.workflow_directory / "modules"
        if not modules_dir.is_dir():
            log.debug(f"No modules directory found at {modules_dir}, skipping")
            return set()

        containers: dict[str, dict[str, str]] = {platform: {} for platform in PLATFORMS}

        with ThreadPoolExecutor() as pool:
            futures = {pool.submit(_process_meta, p): p for p in modules_dir.rglob("meta.yml")}
            for future in as_completed(futures):
                result = future.result()
                if result is None:
                    continue
                module_name, platform_containers = result
                for platform_name, container in platform_containers.items():
                    containers[platform_name][module_name] = container

        log.info("Generated container configs for the pipeline.")

        written: set[str] = set()
        for platform, module_containers in containers.items():
            config_path = self.workflow_directory / "conf" / f"containers_{platform}.config"
            if _write_platform_config(config_path, module_containers, _container_key(platform)):
                written.add(config_path.name)
        return written


def try_generate_container_configs(directory: Path, module_path: Path | None = None) -> None:
    """Regenerate container configs for *directory*.

    If *module_path* is given, only that module's entries are updated (fast
    path for single-module installs).  Otherwise a full scan of ``modules/``
    is performed.
    """
    try:
        configs = ContainerConfigs(directory)
        if module_path is not None:
            configs.update_module_container_config(module_path)
        else:
            configs.generate_container_configs()
    except UserWarning as e:
        log.warning(f"Could not regenerate container configuration files: {e}")
