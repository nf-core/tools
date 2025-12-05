import logging
from pathlib import Path

import yaml

from nf_core.modules.info import ModuleInfo
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, run_cmd

log = logging.getLogger(__name__)


class ModuleContainers:
    """
    Helpers for building, linting and listing module containers.
    """

    def __init__(
        self,
        directory: str | Path = ".",
        remote_url: str | None = None,
        branch: str | None = None,
        no_pull: bool = False,
        hide_progress: bool | None = None,
    ):
        self.directory = Path(directory)
        self.remote_url = remote_url
        self.branch = branch
        self.no_pull = no_pull
        self.hide_progress = hide_progress
        # TODO: save the created containers in this instance

    def create(self, module: str, await_: bool = False, dry_run: bool = False) -> dict[str, dict[str, dict[str, str]]]:
        """
        Build docker and singularity containers for linux/amd64 and linux/arm64 using wave.
        """
        module_dir = self._resolve_module_dir(module)
        env_path = self._environment_path(module_dir)

        containers: dict = {cs: {p: dict() for p in CONTAINER_PLATFORMS} for cs in CONTAINER_SYSTEMS}
        for cs in CONTAINER_SYSTEMS:
            for platform in CONTAINER_PLATFORMS:
                exectuable = "wave"
                args = ["--conda-file", str(env_path), "--freeze", "--platform", platform, "-o yaml"]
                # here "--tower-token" ${{ secrets.TOWER_ACCESS_TOKEN }} --tower-workspace-id ${{ secrets.TOWER_WORKSPACE_ID }}]
                if cs == "singularity":
                    args.append("--singularity")
                if await_:
                    args.append("--await")

                args_str = " ".join(args)
                log.debug(f"Wave command to request container build for {module} ({cs} {platform}): `wave {args_str}`")
                if not dry_run:
                    out = run_cmd(exectuable, args_str)

                    if out is None:
                        raise RuntimeError("Wave command did not return any output")

                    if not out[0]:
                        raise RuntimeError("Wave command did not return any metadata output")

                    try:
                        meta_data = yaml.safe_load(out[0].decode()) or {}
                    except (AttributeError, yaml.YAMLError) as e:
                        raise RuntimeError(f"Could not parse wave YAML metadata for {module} ({cs} {platform})") from e

                    # container = meta_data.get("targetImage") or meta_data.get("containerImage") or ""
                    containers[cs][platform]["name"] = meta_data.get("targetImage") or meta_data.get("containerImage") or ""
                    containers[cs][platform]["buildId"] = meta_data.get("buildId", "")
                    containers[cs][platform]["scanId"] = meta_data.get("scanId", "")
        return containers

    # def conda_lock(self, module: str) -> list[str]:
    #     """
    #     Build a Docker linux/arm64 container and fetch the conda lock file using wave.
    #     """
    #     module_dir = self._resolve_module_dir(module)
    #     env_path = self._environment_path(module_dir)
    #     return ["wave", "--conda-file", str(env_path), "--freeze", "--platform", "linux/arm64", "--await"]

    # def lint(self, module: str) -> list[str]:
    #     """
    #     Confirm containers are defined for the module.
    #     """
    #     return self._containers_from_meta(self._resolve_module_dir(module))

    def list_containers(self, module: str) -> list[tuple[str, str, str]]:
        """
        Return containers defined in the module meta.yml as a list of (<container-system>, <platform>, <image-name>).
        """
        containers_valid = self._containers_from_meta(self, module, self.directory)
        containers_flat = [
            (cs, p, containers_valid[cs][p]["name"]) for cs in CONTAINER_SYSTEMS for p in CONTAINER_PLATFORMS
        ]
        return containers_flat

    def _resolve_module_dir(self, module: str | Path) -> Path:
        if module is None:
            raise ValueError("Please specify a module name.")

        module_dir = Path(self.directory, "modules", "nf-core", module)
        if not module_dir.exists():
            raise ValueError(f"Module '{module}' not found at {module_dir}")

        # TODO: Check if meta.yml and environment.yml are there

        return module_dir

    @staticmethod
    def _environment_path(module_dir: Path) -> Path:
        env_path = module_dir / "environment.yml"
        if not env_path.exists():
            raise FileNotFoundError(f"environment.yml not found for module at {module_dir}")
        return env_path

    @staticmethod
    def _containers_from_meta(cls, module_name: str, dir: Path = Path(".")) -> dict:
        """
        Return containers defined in the module meta.yml.
        """
        module_info = ModuleInfo(dir, module_name)
        module_info.get_component_info()
        if module_info.meta is None:
            raise ValueError(f"The meta.yml for module {module_name} could not be parsed or doesn't exist.")

        containers = module_info.meta.get("containers")
        if not containers:
            raise ValueError(f"Required section 'containers' missing from meta.yaml for module '{module_name}'")

        for system in CONTAINER_SYSTEMS:
            cs = containers.get(system)
            if not cs:
                raise ValueError(f"Container missing for {cs}")

            for pf in CONTAINER_PLATFORMS:
                spec = containers.get(pf)
                if not spec:
                    raise ValueError(f"Platform build {pf} missing for {cs} container for module {module_name}")

        return containers
