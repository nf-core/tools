import json
import logging
from pathlib import Path

import yaml

from nf_core.utils import NF_INSPECT_MIN_NF_VERSION, check_nextflow_version, pretty_nf_version, run_cmd

log = logging.getLogger(__name__)


class ContainerConfigs:
    """Generates the container configuration files for a pipeline.

    Args:
        workflow_directory (str | Path): The directory containing the workflow files.
        org (str): Organisation path.
    """

    def __init__(
        self,
        workflow_directory: Path = Path("."),
        org: str = "nf-core",
    ):
        self.workflow_directory = workflow_directory
        self.org: str = org

    def check_nextflow_version_sufficient(self) -> None:
        """Check if the Nextflow version is sufficient to run `nextflow inspect`."""
        if not check_nextflow_version(NF_INSPECT_MIN_NF_VERSION):
            raise UserWarning(
                f"To use Seqera containers Nextflow version >= {pretty_nf_version(NF_INSPECT_MIN_NF_VERSION)} is required.\n"
                f"Please update your Nextflow version with [magenta]'nextflow self-update'[/]\n"
            )

    def generate_container_configs(self) -> None:
        """
        Generate the container configuration files for a pipeline.
        Requires Nextflow >= 25.04.4
        """
        self.check_nextflow_version_sufficient()
        log.debug("Generating container config file with [magenta bold]nextflow inspect[/].")
        try:
            # Run nextflow inspect
            executable = "nextflow"
            cmd_params = f"inspect -format json {self.workflow_directory}"
            cmd_out = run_cmd(executable, cmd_params)
            if cmd_out is None:
                raise UserWarning("Failed to run `nextflow inspect`. Please check your Nextflow installation.")

            out, _ = cmd_out
            out_json = json.loads(out)

        except RuntimeError as e:
            log.error("Running 'nextflow inspect' failed with the following error:")
            raise UserWarning(e)

        module_names = [p.get("name") for p in out_json["processes"] if p.get("name")]

        platforms: dict[str, list[str]] = {
            "docker_amd64": ["docker", "linux_amd64", "name"],
            "docker_arm64": ["docker", "linux_arm64", "name"],
            "singularity_oras_amd64": ["singularity", "linux_amd64", "name"],
            "singularity_oras_arm64": ["singularity", "linux_arm64", "name"],
            "singularity_https_amd64": ["singularity", "linux_amd64", "https"],
            "singularity_https_arm64": ["singularity", "linux_arm64", "https"],
            "conda_amd64_lockfile": ["conda", "linux_amd64", "lock_file"],
            "conda_arm64_lockfile": ["conda", "linux_arm64", "lock_file"],
        }

        # Build containers dict from module meta.yml files
        # Pre-initialize all platforms to avoid repeated existence checks
        containers: dict[str, dict[str, str]] = {platform: {} for platform in platforms}
        for m_name in module_names:
            # Parse module path once with maxsplit to handle edge cases
            parts = m_name.split("_", 1)
            if len(parts) == 2:
                module_path = Path(parts[0].lower()) / parts[1].lower()
            else:
                module_path = Path(m_name.lower())

            try:
                meta_path = self.workflow_directory / "modules" / self.org / module_path / "meta.yml"
                with open(meta_path) as fh:
                    meta = yaml.safe_load(fh)
            except FileNotFoundError:
                log.warning(f"Could not find meta.yml for {m_name}")
                continue

            # Extract containers for all platforms
            for platform_name, (runtime, arch, protocol) in platforms.items():
                try:
                    containers[platform_name][m_name] = meta["containers"][runtime][arch][protocol]
                except (KeyError, TypeError):
                    log.warning(f"Could not find {platform_name} container for {m_name}")
                    continue

        # write config files
        for platform, module_containers in containers.items():
            if not module_containers:
                continue
            lines = [
                f"process {{ withName: '{module_name}' {{ container = '{container}' }} }}\n"
                for module_name, container in module_containers.items()
            ]
            config_path = self.workflow_directory / "conf" / f"containers_{platform}.config"
            config_path.write_text("".join(lines))
