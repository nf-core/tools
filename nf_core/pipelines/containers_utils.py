import logging
import re
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

    def generate_container_configs(self) -> None:
        """Generate the container configuration files for a pipeline."""
        self.check_nextflow_version_sufficient()
        default_config = self.generate_default_container_config()
        self.generate_all_container_configs(default_config)

    def check_nextflow_version_sufficient(self) -> None:
        """Check if the Nextflow version is sufficient to run `nextflow inspect`."""
        if not check_nextflow_version(NF_INSPECT_MIN_NF_VERSION):
            raise UserWarning(
                f"To use Seqera containers Nextflow version >= {pretty_nf_version(NF_INSPECT_MIN_NF_VERSION)} is required.\n"
                f"Please update your Nextflow version with [magenta]'nextflow self-update'[/]\n"
            )

    def generate_default_container_config(self) -> str:
        """
        Generate the default container configuration file for a pipeline.
        Requires Nextflow >= 25.04.4
        """
        log.debug("Generating container config file with [magenta bold]nextflow inspect[/].")
        try:
            # Run nextflow inspect
            executable = "nextflow"
            cmd_params = f"inspect -format config {self.workflow_directory}"
            cmd_out = run_cmd(executable, cmd_params)
            if cmd_out is None:
                raise UserWarning("Failed to run `nextflow inspect`. Please check your Nextflow installation.")

            out, _ = cmd_out
            out_str = str(out, encoding="utf-8")
            with open(self.workflow_directory / "conf" / "containers_docker_amd64.config", "w") as fh:
                fh.write(out_str)
            log.info(
                f"Generated container config file for Docker AMD64: {self.workflow_directory / 'conf' / 'containers_docker_amd64.config'}"
            )
            return out_str

        except RuntimeError as e:
            log.error("Running 'nextflow inspect' failed with the following error:")
            raise UserWarning(e)

    def generate_all_container_configs(self, default_config: str) -> None:
        """Generate the container configuration files for all platforms."""
        containers: dict[str, dict[str, str]] = {
            "docker_amd64": {},
            "docker_arm64": {},
            "singularity_oras_amd64": {},
            "singularity_oras_arm64": {},
            "singularity_https_amd64": {},
            "singularity_https_arm64": {},
            "conda_amd64_lockfile": {},
            "conda_arm64_lockfile": {},
        }
        for line in default_config.split("\n"):
            if line.startswith("process"):
                pattern = r"process { withName: \'(.*)\' { container = \'(.*)\' } }"
                match = re.search(pattern, line)
                if match:
                    try:
                        module_name = match.group(1)
                        container = match.group(2)
                    except AttributeError:
                        log.warning(f"Could not parse container for process {line}")
                        continue
                else:
                    continue
                containers["docker_amd64"][module_name] = container
        for module_name in containers["docker_amd64"].keys():
            # Find module containers in meta.yml
            if "_" in module_name:
                module_path = Path(module_name.split("_")[0].lower()) / module_name.split("_")[1].lower()
            else:
                module_path = Path(module_name.lower())

            try:
                with open(self.workflow_directory / "modules" / self.org / module_path / "meta.yml") as fh:
                    meta = yaml.safe_load(fh)
            except FileNotFoundError:
                log.warning(f"Could not find meta.yml for {module_name}")
                continue

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

            for p_name, (runtime, arch, protocol) in platforms.items():
                try:
                    containers[p_name][module_name] = meta["containers"][runtime][arch][protocol]
                except KeyError:
                    log.warning(f"Could not find {p_name} container for {module_name}")
                    continue

        # write config files
        for platform in containers.keys():
            with open(self.workflow_directory / "conf" / f"containers_{platform}.config", "w") as fh:
                for module_name in containers[platform].keys():
                    fh.write(
                        f"process {{ withName: '{module_name}' {{ container = '{containers[platform][module_name]}' }} }}\n"
                    )
