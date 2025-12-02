import logging
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


class ModuleContainers:
    """
    Helpers for building, linting and listing module containers.
    """

    def __init__( # not sure how accurate this is...
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

    def create(self, module: str, await_: bool = False) -> list[list[str]]:
        """
        Build docker and singularity containers for linux/amd64 and linux/arm64 using wave.
        """
        # module_dir = self._resolve_module_dir(module)
        # env_path = self._environment_path(module_dir)

        commands: list[list[str]] = []
        for profile in ["docker", "singularity"]:
            for platform in ["linux/amd64", "linux/arm64"]:
                cmd = ["wave", "--conda-file", str(env_path), "--freeze", "--platform", platform]
                # here "--tower-token" ${{ secrets.TOWER_ACCESS_TOKEN }} --tower-workspace-id ${{ secrets.TOWER_WORKSPACE_ID }}]
                if profile == "singularity":
                    cmd.append("--singularity")
                if await_:
                    cmd.append("--await")
                commands.append(cmd)
        return commands

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

    # def list_containers(self, module: str) -> list[str]:
    #     """
    #     Return containers defined in the module meta.yml.
    #     """
    #     return self._containers_from_meta(self._resolve_module_dir(module))

    def _resolve_module_dir(self, module: str) -> Path:
        if module is None:
            raise UserWarning("Please specify a module name.")

        module_path = Path(module)
        if module_path.parts and module_path.parts[0] == "nf-core":
            module_path = Path(*module_path.parts[1:])

        module_dir = self.directory / "modules" / "nf-core" / module_path
        if not module_dir.exists():
            raise LookupError(f"Module '{module}' not found at {module_dir}")
        return module_dir

    @staticmethod
    def _environment_path(module_dir: Path) -> Path:
        env_path = module_dir / "environment.yml"
        if not env_path.exists():
            raise FileNotFoundError(f"environment.yml not found for module at {module_dir}")
        return env_path

    # @staticmethod
    # def _containers_from_meta(module_dir: Path) -> list[str]:
    #     meta_path = module_dir / "meta.yml"
    #     if not meta_path.exists():
    #         raise FileNotFoundError(f"meta.yml not found for module at {module_dir}")

    #     with open(meta_path) as fh:
    #         meta = yaml.safe_load(fh) or {}

    #     containers = meta.get("containers")
    #     if containers is None:
    #         raise UserWarning("No containers defined in meta.yml")
    #     if not isinstance(containers, list):
    #         raise ValueError("Expected 'containers' to be a list in meta.yml")

    #     cleaned = [c for c in containers if c is not None and str(c).strip()]
    #     if len(cleaned) != len(containers):
    #         raise UserWarning("Empty container entries found in meta.yml")
    #     if len(cleaned) == 0:
    #         raise UserWarning("No containers defined in meta.yml")

    #     return cleaned
