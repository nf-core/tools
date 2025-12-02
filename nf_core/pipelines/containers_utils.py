import logging
from pathlib import Path

from nf_core.utils import NF_INSPECT_MIN_NF_VERSION, check_nextflow_version, pretty_nf_version, run_cmd

log = logging.getLogger(__name__)


class ContainerConfigs:
    """Generates the container configuration files for a pipeline.

    Args:
        workflow_directory (str | Path): The directory containing the workflow files.
    """

    def __init__(
        self,
        workflow_directory: str | Path = ".",
    ):
        self.workflow_directory = Path(workflow_directory)

    def check_nextflow_version(self) -> None:
        """Check if the Nextflow version is sufficient to run `nextflow inspect`."""
        if not check_nextflow_version(NF_INSPECT_MIN_NF_VERSION):
            raise UserWarning(
                f"To use Seqera containers Nextflow version >= {pretty_nf_version(NF_INSPECT_MIN_NF_VERSION)} is required.\n"
                f"Please update your Nextflow version with [magenta]'nextflow self-update'[/]\n"
            )

    def generate_default_container_config(self) -> None:
        """
        Generate the default container configuration file for a pipeline.
        Requires Nextflow >= 25.04.4
        """
        self.check_nextflow_version()
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
            with open(self.workflow_directory / "configs" / "containers_docker_amd64.config", "w") as fh:
                fh.write(out_str)
            log.info(
                f"Generated container config file for Docker AMD64: {self.workflow_directory / 'configs' / 'containers_docker_amd64.config'}"
            )

        except RuntimeError as e:
            log.error("Running 'nextflow inspect' failed with the following error:")
            raise UserWarning(e)
