import contextlib
import logging
import re
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

_PROCESS_NAME_RE = re.compile(r"^\s*process\s+(\w+)\s*\{", re.MULTILINE)

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


class ContainerConfigs:
    """Generates the container configuration files for a pipeline.

    Args:
        workflow_directory (Path): The directory containing the workflow files.
    """

    def __init__(
        self,
        workflow_directory: Path = Path(),
    ):
        self.workflow_directory = workflow_directory

    def generate_container_configs(
        self, new_module_path: Path | None = None, new_module_name: str | None = None
    ) -> set[str]:
        """
        Generate the container configuration files for a pipeline by scanning
        all ``main.nf`` files under the ``modules/`` directory and reading the
        accompanying ``meta.yml`` for container information.

        Returns:
            set[str]: Names of config files written (e.g. ``{'containers_docker_amd64.config'}``).
        """
        containers: dict[str, dict[str, str]] = {platform: {} for platform in PLATFORMS}

        for meta_path in (self.workflow_directory / "modules").rglob("meta.yml"):
            try:
                content = meta_path.read_text()
            except OSError as e:
                log.debug(f"Could not read {meta_path}: {e}")
                continue

            # TODO: remove this early-exit once containers are present in the majority of modules
            if "containers:" not in content:
                continue

            meta = yaml.safe_load(content)

            main_nf = meta_path.parent / "main.nf"
            try:
                match = _PROCESS_NAME_RE.search(main_nf.read_text())
            except OSError:
                log.debug(f"No main.nf next to {meta_path}, skipping")
                continue
            if not match:
                log.debug(f"No process definition found in {main_nf}, skipping")
                continue
            process_name = match.group(1)

            for platform_name, (runtime, arch, protocol) in PLATFORMS.items():
                with contextlib.suppress(KeyError, TypeError):
                    containers[platform_name][process_name] = meta["containers"][runtime][arch][protocol]

        log.info("Generated container configs for the pipeline.")

        # remove all generated config files, to handle removed modules
        for platform in PLATFORMS:
            (self.workflow_directory / "conf" / f"containers_{platform}.config").unlink(missing_ok=True)
        # write config files
        written: set[str] = set()
        for platform, module_containers in containers.items():
            if not module_containers:
                continue
            container_key = "conda" if platform.startswith("conda_lock_") else "container"
            lines = [
                f"process {{ withName: '{module_name}' {{ {container_key} = '{container}' }} }}\n"
                for module_name, container in sorted(module_containers.items())
            ]
            config_path = self.workflow_directory / "conf" / f"containers_{platform}.config"
            config_path.write_text("".join(lines))
            written.add(config_path.name)
        return written


def try_generate_container_configs(
    directory: Path, new_module_path: Path | None = None, new_module_name: str | None = None
) -> None:
    try:
        ContainerConfigs(directory).generate_container_configs(new_module_path, new_module_name)
    except UserWarning as e:
        log.warning(f"Could not regenerate container configuration files: {e}")
