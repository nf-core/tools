import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote

import requests
import yaml

from nf_core.components.components_utils import yaml as ruamel_yaml
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.lint import ModuleLint
from nf_core.modules.modules_utils import prompt_module_selection
from nf_core.pipelines.lint_utils import run_prettier_on_file
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
    HTTPS_URL_KEY = "https"

    def __init__(self, module: str | None, directory: str | Path = "."):
        self.directory = Path(directory)

        # Initialize list of available modules for the prompt
        self.all_remote_components = self._get_available_modules()

        # Prompt for module selection if not provided
        if module is None and len(self.all_remote_components) > 0:
            module = prompt_module_selection(
                self.all_remote_components, component_type="modules", action="Build containers for"
            )

        self.module = module

        # Use NFCoreComponent to handle module directory and file paths
        self.nfcore_component = self._init_nfcore_component(module)
        self.module_directory = self.nfcore_component.component_dir
        self.environment_yml = self.nfcore_component.environment_yml
        self.meta_yml = self.nfcore_component.meta_yml
        self.containers: dict | None = None

    def _get_available_modules(self) -> list[NFCoreComponent]:
        """Get list of available modules based on repository type."""
        from nf_core.components.components_utils import get_repo_info
        from nf_core.modules.modules_json import ModulesJson

        try:
            # Detect repository type
            _, repo_type, org = get_repo_info(self.directory, use_prompt=False)
        except (UserWarning, FileNotFoundError):
            log.debug("Could not determine repository type")
            return []

        modules = []

        if repo_type == "pipeline":
            # Get modules from modules.json
            modules_json_path = self.directory / "modules.json"
            if modules_json_path.exists():
                try:
                    modules_json = ModulesJson(self.directory)
                    for repo_url, components in modules_json.get_all_components("modules").items():
                        if isinstance(components, str):
                            log.warning(f"Error parsing modules.json: {components}")
                            continue
                        for org_name, module_name in components:
                            modules.append(
                                NFCoreComponent(
                                    module_name,
                                    repo_url,
                                    self.directory / "modules" / org_name / module_name,
                                    repo_type,
                                    self.directory,
                                    "modules",
                                )
                            )
                except Exception as e:
                    log.debug(f"Error loading modules from modules.json: {e}")

        elif repo_type == "modules":
            # Get modules from modules directory
            modules_dir = self.directory / "modules" / "nf-core"
            if modules_dir.exists():
                for main_nf in modules_dir.rglob("main.nf"):
                    module_name = str(main_nf.parent.relative_to(modules_dir))
                    modules.append(
                        NFCoreComponent(
                            module_name,
                            None,
                            modules_dir / module_name,
                            repo_type,
                            self.directory,
                            "modules",
                        )
                    )

        return modules

    def _init_nfcore_component(self, module: str) -> NFCoreComponent:
        """Initialize NFCoreComponent for the module."""
        return NFCoreComponent(
            component_name=module,
            repo_url="https://github.com/nf-core/modules.git",
            component_dir=self.directory,
            repo_type="modules",
            base_dir=self.directory,
            component_type="modules",
            remote_component=True,
        )

    def create(self, await_: bool = False) -> dict[str, dict[str, dict[str, str]]]:
        """
        Build docker and singularity containers for linux/amd64 and linux/arm64 using wave.
        """
        containers: dict = {cs: {p: dict() for p in CONTAINER_PLATFORMS} for cs in CONTAINER_SYSTEMS}
        tasks = dict()
        threads = max(len(CONTAINER_SYSTEMS) * len(CONTAINER_PLATFORMS), 1)

        assert self.environment_yml is not None
        with ThreadPoolExecutor(max_workers=threads) as pool:
            for cs in CONTAINER_SYSTEMS:
                for platform in CONTAINER_PLATFORMS:
                    fut = pool.submit(self.request_container, cs, platform, self.environment_yml, await_)
                    tasks[fut] = (cs, platform)

        for fut in as_completed(tasks):
            cs, platform = tasks[fut]
            # Add container info for all container systems
            containers[cs][platform] = fut.result()

            # Add conda lock information based on info for docker container
            if cs != "docker":
                continue

            build_id = containers[cs][platform].get(self.BUILD_ID_KEY, "")
            if not build_id:
                log.debug("Docker image for {platform} missing - Conda-lock skipped")
                continue

            conda_data = containers.get("conda", dict())
            conda_data.update({platform: {self.LOCK_FILE_KEY: self.get_conda_lock_url(build_id)}})
            containers["conda"] = conda_data

        self.containers = containers
        return containers

    @classmethod
    def request_container(cls, container_system: str, platform: str, conda_file: Path, await_build=False) -> dict:
        assert conda_file.exists()
        assert container_system in CONTAINER_SYSTEMS
        assert platform in CONTAINER_PLATFORMS

        container: dict[str, str] = dict()
        executable = "wave"
        args = ["--conda-file", str(conda_file.absolute()), "--freeze", "--platform", platform, "-o yaml"]
        if container_system == "singularity":
            args.append("--singularity")
        if await_build:
            args.append("--await")

        args_str = " ".join(args)
        log.debug(f"Wave command to request container ({container_system} {platform}): `wave {args_str}`")
        out = run_cmd(executable, args_str)

        if out is None:
            raise RuntimeError("Wave command did not return any output")

        try:
            meta_data = yaml.safe_load(out[0].decode()) or dict()
        except (KeyError, AttributeError, yaml.YAMLError) as e:
            log.debug(f"Output yaml from wave build command: {out}")
            raise RuntimeError(f"Could not parse wave YAML metadata ({container_system} {platform})") from e

        image = meta_data.get("targetImage") or meta_data.get("containerImage") or ""
        if not image:
            raise RuntimeError(f"Wave build ({container_system} {platform}) did not return an image name")

        container[cls.IMAGE_KEY] = image

        build_id = meta_data.get(cls.BUILD_ID_KEY, "")
        if build_id:
            container[cls.BUILD_ID_KEY] = build_id

        if container_system == "docker":
            scan_id = meta_data.get(cls.SCAN_ID_KEY, "")
            if scan_id:
                container[cls.SCAN_ID_KEY] = scan_id

        if container_system == "singularity" and not await_build:
            log.warning(
                "Cannot retrieve https-url by inspecting the image, when the image build is not awaited. Rerun the command with `--await`"
            )

        elif container_system == "singularity":
            inspect_out = cls.request_image_inspect(image)
            container_layers = inspect_out.get("container", dict()).get("manifest", dict()).get("layers", dict())

            if not (
                len(container_layers) == 1
                and container_layers[0].get("mediaType", "").endswith(".sif")
                and container_layers[0].get("digest")
            ):
                log.warning(f"Https-url for image {image} could not be extracted from image inspect output")

            else:
                log.debug(f"Extracting https-uri for {image} from image inspect: {container_layers[0]}")
                digest = container_layers[0]["digest"].replace("sha256:", "")
                container[cls.HTTPS_URL_KEY] = (
                    f"https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/{digest[:2]}/{digest}/data"
                )

        return container

    @classmethod
    def request_image_inspect(cls, image: str) -> dict:
        """
        Request wave container inspect.
        """
        executable = "wave"
        args = ["--inspect", "-o yaml", "-i", image]

        args_str = " ".join(args)
        log.debug(f"Wave command to request image inspect for image {image}: `wave {args_str}`")
        out = run_cmd(executable, args_str)

        if out is None:
            raise RuntimeError("Wave command did not return any output")

        try:
            inspect_out = yaml.safe_load(out[0].decode()) or dict()
        except (KeyError, AttributeError, yaml.YAMLError) as e:
            log.debug(f"Output yaml from wave build command: {out}")
            raise RuntimeError(f"Could not parse wave inspect yaml output for image {image}") from e

        return inspect_out

    @staticmethod
    def get_conda_lock_url(build_id) -> str:
        build_id_safe = quote(build_id, safe="")
        url = f"https://wave.seqera.io/v1alpha1/builds/{build_id_safe}/condalock"
        return url

    def get_conda_lock_file(self, platform: str) -> str:
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

        return self.request_conda_lock_file(conda_lock_url)

    @staticmethod
    def request_conda_lock_file(conda_lock_url: str) -> str:
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

    def get_meta(self) -> dict:
        """Load and return the meta.yml content."""
        if not self.meta_yml or not self.meta_yml.exists():
            raise FileNotFoundError(f"meta.yml not found for module '{self.module}'")
        with open(self.meta_yml) as f:
            meta = ruamel_yaml.load(f)
        return meta

    def get_containers_from_meta(self) -> dict:
        """
        Return containers defined in the module meta.yml.
        """
        assert self.meta_yml and self.meta_yml.exists()

        meta = self.get_meta()
        containers = meta.get("containers", dict())
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

    def update_containers_in_meta(self, module_lint: ModuleLint | None = None) -> None:
        """
        Update the containers section in meta.yml.

        Args:
            module_lint: Optional ModuleLint instance to use for sorting.
                        If not provided, a new instance will be created.
        """
        if self.containers is None:
            log.debug("Containers not initialized - running `create()` ...")
            self.create()

        meta = self.get_meta()
        meta_containers = meta.get("containers", dict())
        meta_containers.update(self.containers)
        meta["containers"] = meta_containers

        # Sort the YAML according to the schema's property order using ModuleLint
        if module_lint is None:
            try:
                module_lint = ModuleLint(self.directory)
            except Exception as e:
                log.warning(f"Failed to initialize ModuleLint for sorting: {e}")

        if module_lint is not None:
            try:
                meta = module_lint.sort_meta_yml(meta)
            except Exception as e:
                log.warning(f"Failed to sort meta.yml: {e}")

        assert self.meta_yml and self.meta_yml.exists()

        with open(self.meta_yml, "w") as f:
            ruamel_yaml.dump(meta, f)

        # Format with prettier for consistent styling
        try:
            run_prettier_on_file(self.meta_yml)
        except Exception as e:
            log.debug(f"Could not run prettier on meta.yml: {e}")
