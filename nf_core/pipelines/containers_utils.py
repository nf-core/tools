import json
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

    def check_nextflow_version_sufficient(self) -> None:
        """Check if the Nextflow version is sufficient to run `nextflow inspect`."""
        if not check_nextflow_version(NF_INSPECT_MIN_NF_VERSION):
            raise UserWarning(
                f"To use Seqera containers Nextflow version >= {pretty_nf_version(NF_INSPECT_MIN_NF_VERSION)} is required.\n"
                f"Please update your Nextflow version with [magenta]'nextflow self-update'[/]\n"
            )

    def parse_module_paths(self) -> dict[str, Path]:
        """Parse include statements from workflow files to extract module paths.

        Only processes includes pointing to 'modules/' directories.
        Extracts the path from 'modules/' onwards, ignoring any '../' prefixes.

        Returns:
            dict: Mapping of process names to their module paths (e.g., 'modules/nf-core/fastqc')
        """
        module_paths = {}

        # Pattern matches: include { NAME ... } from 'path'
        # Captures the first name (original) and the path, ignoring any alias
        include_pattern = re.compile(r"include\s*\{\s*(\w+).*?\}\s*from\s+['\"]([^'\"]+)['\"]")

        # Search in workflows, modules, and subworkflows directories
        search_dirs = ["workflows", "modules", "subworkflows"]

        for search_dir in search_dirs:
            search_path = self.workflow_directory / search_dir
            if not search_path.exists():
                continue

            for nf_file in search_path.rglob("*.nf"):
                try:
                    content = nf_file.read_text()
                    for match in include_pattern.finditer(content):
                        process_name = match.group(1)
                        relative_path = match.group(2)

                        # Only process paths that contain 'modules/'
                        if "modules/" not in relative_path:
                            continue

                        # Extract everything from 'modules/' onwards, removing any '/main' suffix
                        module_path_str = relative_path[relative_path.find("modules/") :]
                        module_path_str = module_path_str.replace("/main", "")

                        module_paths[process_name] = Path(module_path_str)
                        log.debug(f"Found include: {process_name} -> {module_path_str}")

                except Exception as e:
                    log.debug(f"Error parsing {nf_file}: {e}")
                    continue

        return module_paths

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
        log.debug(f"Found {len(module_names)} modules: {', '.join(module_names)}")

        # Parse module paths from include statements
        module_path_map = self.parse_module_paths()
        log.debug(f"Parsed {len(module_path_map)} module paths from include statements")

        platforms: dict[str, list[str]] = {
            "docker_amd64": ["docker", "linux/amd64", "name"],
            "docker_arm64": ["docker", "linux/arm64", "name"],
            "singularity_oras_amd64": ["singularity", "linux/amd64", "name"],
            "singularity_oras_arm64": ["singularity", "linux/arm64", "name"],
            "singularity_https_amd64": ["singularity", "linux/amd64", "https"],
            "singularity_https_arm64": ["singularity", "linux/arm64", "https"],
            "conda_lock_files_amd64": ["conda", "linux/amd64", "lock_file"],
            "conda_lock_files_arm64": ["conda", "linux/arm64", "lock_file"],
        }

        # Build containers dict from module meta.yml files
        # Pre-initialize all platforms to avoid repeated existence checks
        containers: dict[str, dict[str, str]] = {platform: {} for platform in platforms}
        for m_name in module_names:
            # Try to get module path from include statements
            if m_name in module_path_map:
                module_path = module_path_map[m_name]
                log.debug(f"Using parsed path for {m_name}: {module_path}")
            else:
                # Fallback to old heuristic method
                log.debug(f"No parsed path found for {m_name}, using heuristic")
                parts = m_name.split("_", 1)
                if len(parts) == 2:
                    module_path = Path(parts[0].lower()) / parts[1].lower()
                else:
                    module_path = Path(m_name.lower())

            # Look for meta.yml in the module path
            meta_path = self.workflow_directory / module_path / "meta.yml"

            try:
                with open(meta_path) as fh:
                    meta = yaml.safe_load(fh)
                    log.debug(f"Loaded meta.yml for {m_name} from {meta_path}")
            except FileNotFoundError:
                log.warning(f"Could not find meta.yml for {m_name} at {meta_path}")
                continue

            # Extract containers for all platforms
            has_warnings = False
            for platform_name, (runtime, arch, protocol) in platforms.items():
                try:
                    containers[platform_name][m_name] = meta["containers"][runtime][arch][protocol]
                except (KeyError, TypeError):
                    log.debug(f"Could not find {platform_name} container for {m_name}")
                    has_warnings = True
                    continue
        if has_warnings:
            log.info(
                "Generated container configs for the pipeline. Not all containers were found. Run with `-v` to see detailed warning messages."
            )
        else:
            log.info("Generated container configs for the pipeline successfully.")

        # write config files
        for platform, module_containers in containers.items():
            if not module_containers:
                continue
            lines = [
                f"process {{ withName: '{module_name}' {{ container = '{container}' }} }}\n"
                for module_name, container in sorted(module_containers.items())
            ]
            config_path = self.workflow_directory / "conf" / f"containers_{platform}.config"
            config_path.write_text("".join(lines))
