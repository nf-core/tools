import logging
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

from nf_core.modules.info import ModuleInfo
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, run_cmd

log = logging.getLogger(__name__)


class ModuleContainers:
    """
    Helpers for building, linting and listing module containers.
    """

    IMAGE_KEY = "name"
    BUILD_ID_KEY = "buildId"
    SCAN_ID_KEY = "scanId"
    LOCK_FILE_KEY = "lock_file"

    def __init__(self, module: str, directory: str | Path = "."):
        self.directory = Path(directory)
        self.module = module
        self.module_directory = self.get_module_dir(module)
        self.condafile = self.get_environment_path(self.module_directory)
        self.metafile = self.get_metayaml_path(self.module_directory)
        self.containers: dict | None = None

    def create(self, await_: bool = False, dry_run: bool = False) -> dict[str, dict[str, dict[str, str]]]:
        """
        Build docker and singularity containers for linux/amd64 and linux/arm64 using wave.
        """
        containers: dict = {cs: {p: dict() for p in CONTAINER_PLATFORMS} for cs in CONTAINER_SYSTEMS}
        for cs in CONTAINER_SYSTEMS:
            for platform in CONTAINER_PLATFORMS:
                containers[cs][platform] = self.request_container(cs, platform, self.condafile, await_, dry_run)

        for platform in CONTAINER_PLATFORMS:
            build_id = containers.get("docker", dict()).get(platform, dict()).get(self.BUILD_ID_KEY, "")
            if not build_id:
                log.debug("Docker image for {platform} missing - Conda-lock skipped")
                continue

            conda_data = containers.get("conda", dict())
            conda_data.update({platform: {self.LOCK_FILE_KEY: self.get_conda_lock_url(build_id)}})
            containers["conda"] = conda_data

        self.containers = containers
        return containers

    @classmethod
    def request_container(
        cls, container_system: str, platform: str, conda_file: Path, await_build=False, dry_run=False
    ) -> dict:
        assert conda_file.exists()
        assert container_system in CONTAINER_SYSTEMS
        assert platform in CONTAINER_PLATFORMS

        container: dict[str, str] = dict()
        exectuable = "wave"
        args = ["--conda-file", str(conda_file.absolute()), "--freeze", "--platform", str(platform), "-o yaml"]
        if container_system == "singularity":
            args.append("--singularity")
        if await_build:
            args.append("--await")

        args_str = " ".join(args)
        log.debug(f"Wave command to request container ({container_system} {platform}): `wave {args_str}`")
        if not dry_run:
            out = run_cmd(exectuable, args_str)

            if out is None:
                raise RuntimeError("Wave command did not return any output")

            try:
                meta_data = yaml.safe_load(out[0].decode()) or dict()
            except (KeyError, AttributeError, yaml.YAMLError) as e:
                log.debug(f"Output yaml from wave build command: {out}")
                raise RuntimeError(f"Could not parse wave YAML metadata ({container_system} {platform})") from e

            image = meta_data.get("targetImage") or meta_data.get("containerImage") or ""
            if not image:
                raise RuntimeError(f"Wave build ({container_system} {platform}) did not return a image name")

            container[cls.IMAGE_KEY] = image

            build_id = meta_data.get(cls.BUILD_ID_KEY, "")
            if build_id:
                container[cls.BUILD_ID_KEY] = build_id

            scan_id = meta_data.get(cls.SCAN_ID_KEY, "")
            if scan_id:
                container[cls.SCAN_ID_KEY] = scan_id

        return container

    @staticmethod
    def get_conda_lock_url(build_id) -> str:
        build_id_safe = quote(build_id, safe="")
        url = f"https://wave.seqera.io/v1alpha1/builds/{build_id_safe}/condalock"
        return url

    def conda_lock(self, platform: str) -> str:
        """
        Get the conda lock file for an existing environment.
        Try (in that order):
            1. reading from meta.yml
            2. reading from cached containers
            3. recreating with wave commands
        """
        assert platform in CONTAINER_PLATFORMS

        containers = self.containers or self.get_containers_from_meta() or self.create() or dict()

        conda_lock_url = containers.get("conda", dict()).get(platform, dict()).get(self.LOCK_FILE_KEY)
        if not conda_lock_url:
            raise ValueError("")

        return self.request_conda_lock(conda_lock_url)

    @staticmethod
    def request_conda_lock(conda_lock_url: str) -> str:
        resp = requests.get(conda_lock_url)
        return resp.text

    # def lint(self, module: str) -> list[str]:
    #     """
    #     Confirm containers are defined for the module.
    #     """
    #     return self._containers_from_meta(self._resolve_module_dir(module))

    def list_containers(self) -> list[tuple[str, str, str]]:
        """
        Return containers defined in the module meta.yml as a list of (<container-system>, <platform>, <image-name>).
        """
        containers_valid = self.get_containers_from_meta()
        containers_flat = [
            (cs, p, containers_valid[cs][p]["name"]) for cs in CONTAINER_SYSTEMS for p in CONTAINER_PLATFORMS
        ]
        return containers_flat

    def get_module_dir(self, module: str | Path) -> Path:
        if module is None:
            raise ValueError("Please specify a module name.")

        module_dir = Path(self.directory, "modules", "nf-core", module)
        if not module_dir.exists():
            raise ValueError(f"Module '{module}' not found at {module_dir}")

        return module_dir

    @staticmethod
    def get_environment_path(module_dir: Path) -> Path:
        env_path = module_dir / "environment.yml"
        if not env_path.exists():
            raise FileNotFoundError(f"environment.yml not found for module at {module_dir}")
        return env_path

    @staticmethod
    def get_metayaml_path(module_dir: Path) -> Path:
        metayaml_path = module_dir / "meta.yaml"
        if not metayaml_path.exists():
            raise FileNotFoundError(f"meta.yml not found for module at {module_dir}")
        return metayaml_path

    def get_containers_from_meta(self) -> dict:
        """
        Return containers defined in the module meta.yml.
        """
        module_info = ModuleInfo(dir, self.module)
        module_info.get_component_info()
        if module_info.meta is None:
            raise ValueError(f"The meta.yml for module {self.module} could not be parsed or doesn't exist.")

        containers = module_info.meta.get("containers", dict())
        if not containers:
            log.warning(f"Section 'containers' missing from meta.yaml for module '{self.module}'")

        for system in CONTAINER_SYSTEMS:
            cs = containers.get(system)
            if not cs:
                raise ValueError(f"Container missing for {cs}")

            for pf in CONTAINER_PLATFORMS:
                spec = containers.get(pf)
                if not spec:
                    raise ValueError(f"Platform build {pf} missing for {cs} container for module {self.module}")

        return containers

    def update_containers_in_meta(self) -> None:
        if self.containers is None:
            log.debug("Containers not initialized - running `create()` ...")
            self.create()

        with open(self.metafile, "rw") as f:
            meta = yaml.safe_load(f.read())
            meta.get("containers").update(self.containers)
            # TODO container-conversion: sort the yaml (again) -> call linting?
            out = yaml.dump(meta)
            f.write(out)
