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
        workflow_directory: str | Path = ".",
        org: str = "nf-core",
    ):
        self.workflow_directory = Path(workflow_directory)
        self.org: str = org

    def generate_container_configs(self) -> None:
        """Generate the container configuration files for a pipeline."""
        self.check_nextflow_version()
        default_config = self.generate_default_container_config()
        self.generate_all_container_configs(default_config)

    def check_nextflow_version(self) -> None:
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
                pattern = r"process { withName: \'(.*)\' { container = \'(.*)\' } }\n"
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
                with open(self.workflow_directory / "modules" / module_path / self.org / "meta.yml") as fh:
                    meta = yaml.safe_load(fh)
            except FileNotFoundError:
                log.warning(f"Could not find meta.yml for {module_name}")
                continue

            try:
                containers["docker_arm64"][module_name] = meta["containers"]["docker"]["linux_arm64"]["name"]
            except KeyError:
                log.warning(f"Could not find docker linux_arm64 container for {module_name}")
                continue
            try:
                containers["singularity_oras_amd64"][module_name] = meta["containers"]["singularity"]["linux_amd64"][
                    "name"
                ]
            except KeyError:
                log.warning(f"Could not find singularity linux_amd64 oras container for {module_name}")
                continue
            try:
                containers["singularity_oras_arm64"][module_name] = meta["containers"]["singularity"]["linux_arm64"][
                    "name"
                ]
            except KeyError:
                log.warning(f"Could not find singularity linux_arm64 oras container for {module_name}")
                continue
            try:
                containers["singularity_https_amd64"][module_name] = meta["containers"]["singularity"]["linux_amd64"][
                    "https"
                ]
            except KeyError:
                log.warning(f"Could not find singularity linux_amd64 https URL for {module_name}")
                continue
            try:
                containers["singularity_https_arm64"][module_name] = meta["containers"]["singularity"]["linux_arm64"][
                    "https"
                ]
            except KeyError:
                log.warning(f"Could not find singularity linux_arm64 https URL for {module_name}")
                continue
            try:
                containers["conda_amd64_lockfile"][module_name] = meta["containers"]["conda"]["linux_amd64"][
                    "lock_file"
                ]
            except KeyError:
                log.warning(f"Could not find conda linux_amd64 lock file for {module_name}")
                continue
            try:
                containers["conda_arm64_lockfile"][module_name] = meta["containers"]["conda"]["linux_arm64"][
                    "lock_file"
                ]
            except KeyError:
                log.warning(f"Could not find conda linux_arm64 lock file for {module_name}")
                continue

        # write config files
        for platform in containers.keys():
            with open(self.workflow_directory / "conf" / f"containers_{platform}.config", "w") as fh:
                for module_name in containers[platform].keys():
                    fh.write(
                        f"process {{ withName: '{module_name}' {{ container = {containers[platform][module_name]}' }} }}\n"
                    )
