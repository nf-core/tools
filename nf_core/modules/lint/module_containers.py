import logging
from pathlib import Path

import requests
from pydantic_core import ValidationError

from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.modules_utils import ContainerEntry, MetaYmlContainers, module_uses_dockerfile
from nf_core.utils import CONTAINER_PLATFORMS

log = logging.getLogger(__name__)


def lint_meta_yml_containers(module: NFCoreComponent, skip_docker=False, skip_conda=False, skip_singularity=False):
    if module_uses_dockerfile(module):
        log.info(f"Module '{module.component_name}' uses a Dockerfile - skipping container lint")
        return

    meta_path = Path(module.component_dir, "meta.yml")
    meta_yml = module.load_meta_yml()
    assert meta_yml and "containers" in meta_yml

    containers_raw = meta_yml["containers"]

    # Protocol and hash checks for docker/singularity
    skip_system = {"docker": skip_docker, "singularity": skip_singularity, "conda": skip_conda}

    # Maps system name to per-platform container model.
    # Instantiate individual models separately for per-system
    # error handling and skipping
    container_models = {
        "docker": MetaYmlContainers.DockerContainer,
        "singularity": MetaYmlContainers.SingularityContainer,
        "conda": MetaYmlContainers.CondaEnvironment,
    }

    # Collect the instantiated pydantic submodels of MetaYmlContainers manually
    containers = MetaYmlContainers()
    assert all(hasattr(containers, system_key) for system_key in (*skip_system.keys(), *container_models.keys()))

    for system_key in container_models:
        if skip_system[system_key]:
            continue

        for platform in CONTAINER_PLATFORMS:
            if platform not in containers_raw.get(system_key, {}):
                module.failed.append(
                    (
                        "meta_yml",
                        f"container_section_{system_key}",
                        f"No entries found for expected platform: {platform}",
                        meta_path,
                    )
                )
                continue
            else:
                module.passed.append(
                    (
                        "meta_yml",
                        f"container_section_{system_key}",
                        f"Subsection for platform {platform} exists",
                        meta_path,
                    )
                )

            try:
                model = container_models[system_key]
                assert hasattr(model, "model_validate")
                system = model.model_validate(containers_raw[system_key][platform])
                _systems = getattr(containers, system_key) or {}
                _systems[platform] = system
                setattr(containers, system_key, _systems)

            except ValidationError as e:
                # TODO / NOTE: These warnings are already be caught by schema validation
                # TODO / NOTE: This also replaces individual checks for existance of container definitions
                #  for all platform in CONTAINER_SYSTEMS
                error_msg = f"{platform} subsection has errors. "
                error_msg += ", ".join([f"{str(err['loc'])}: {err['msg']}" for err in e.errors()])
                module.failed.append(("meta_yml", f"containers_section_{system_key}", error_msg, meta_path))
                continue
            else:
                module.passed.append(
                    (
                        "meta_yml",
                        f"containers_section_{system_key}",
                        f"{platform} subsection parsed correctly",
                        meta_path,
                    )
                )

            if system_key == "conda":
                continue

            # check build_id hash matches hash in container tag
            build_id_clean = system.build_id.lstrip("bd-")

            if not build_id_clean:
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_build_id_hash",
                        f"No build_id found for {system_key} {platform}",
                        meta_path,
                    )
                )
                continue

            parts = build_id_clean.split("_")
            build_hash = parts[0] if parts else ""

            name_clean = system.name
            if "://" in name_clean:
                name_clean = system.name.split("://", 1)[1]
            if "@" in name_clean:
                name_clean = name_clean.split("@", 1)[0]
            if ":" not in name_clean:
                name_hash = ""
            else:
                tag = name_clean.rsplit(":", 1)[1]
                if "--" in tag:
                    name_hash = tag.rsplit("--", 1)[1]
                else:
                    tag = name_no_scheme.rsplit(":", 1)[1]
                    if "--" in tag:
                        name_hash = tag.rsplit("--", 1)[1]
                    else:
                        tag_lower = tag.lower()
                        if len(tag_lower) >= 8 and all(c in "0123456789abcdef" for c in tag_lower):
                            name_hash = tag
                        else:
                            name_hash = ""
                if build_hash and name_hash:
                    if build_hash != name_hash:
                        module.failed.append(
                            (
                                "meta_yml",
                                "containers_build_id_hash",
                                f"Build ID `{build_hash}` hash does not match {system} container tag `{name_hash}` for {platform}",
                                meta_path,
                            )
                        )
                    else:
                        module.passed.append(
                            (
                                "meta_yml",
                                "containers_build_id_hash",
                                f"Build ID hash matches {system} container tag for {platform}",
                                meta_path,
                            )
                        )
                else:
                    module.warned.append(
                        (
                            "meta_yml",
                            "containers_build_id_hash",
                            f"Could not compare build ID hash with {system} container tag for {platform}, because either build_hash:`{build_hash}` or  name_hash:`{name_hash}` is `None`.",
                            meta_path,
                        )
                    )
            else:
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_build_id_hash",
                        f"Could not compare build ID hash with {system} container tag for {platform}",
                        meta_path,
                    )
                )

    # Check docker container images exist for all platforms (unless skipped)
    if skip_docker:
        pass
    elif not containers.docker:
        module.warned.append(
            ("meta_yml", "containers_docker_exist", "Docker containers section missing or empty", meta_path)
        )
    else:
        for platform in containers.docker:
            docker_name = containers.docker[platform].name
            if not docker_name:
                module.warned.append(
                    (
                        "meta_yml",
                        f"containers_docker_{platform}_exists",
                        f"Docker {platform} container name missing",
                        meta_path,
                    )
                )
                continue
            if docker_name.startswith(("http://", "https://")):
                docker_url = docker_name
            elif "://" in docker_name:
                docker_url = ""
            else:
                docker_url = f"https://{docker_name}"
            if not docker_url:
                module.warned.append(
                    (
                        "meta_yml",
                        f"containers_docker_{platform}_exists",
                        f"Docker {platform} container has non-http protocol; existence check skipped",
                        meta_path,
                    )
                )
            else:
                try:
                    response = requests.head(docker_url, stream=True, allow_redirects=True)
                    if response.ok:
                        module.passed.append(
                            (
                                "meta_yml",
                                f"containers_docker_{platform}_exists",
                                f"Docker {platform} image exists",
                                meta_path,
                            )
                        )
                    else:
                        module.warned.append(
                            (
                                "meta_yml",
                                f"containers_docker_{platform}_exists",
                                f"Docker {platform} image not reachable (status {response.status_code})",
                                meta_path,
                            )
                        )
                except requests.RequestException as e:
                    module.warned.append(
                        (
                            "meta_yml",
                            f"containers_docker_{platform}_exists",
                            f"Unable to connect to docker image URL: {e}",
                            meta_path,
                        )
                    )

    # Conda lock files and hash checks
    if skip_conda:
        pass
    elif not containers.conda:
        module.warned.append(
            ("meta_yml", "containers_conda_lock_exists", "Conda containers section missing or empty", meta_path)
        )
    else:
        for platform in containers.conda:
            lock_file = containers.conda[platform].lock_file
            if not lock_file:
                module.warned.append(
                    ("meta_yml", "containers_conda_lock_exists", f"Missing conda lock_file for {platform}", meta_path)
                )
                continue
            lock_path = Path(lock_file)
            if lock_path.exists():
                module.passed.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_exists",
                        f"Conda lock_file exists for {platform}",
                        meta_path,
                    )
                )
            else:
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_exists",
                        f"Conda lock_file not found for {platform}: {lock_path}",
                        meta_path,
                    )
                )

        for plat in CONTAINER_PLATFORMS:
            _docker_plat = docker_containers.get(plat) if isinstance(docker_containers, dict) else None
            docker_plat: dict = _docker_plat if isinstance(_docker_plat, dict) else {}
            docker_build_id = (
                docker_plat.get("buildId") or docker_plat.get("build_id") or docker_plat.get("buildid") or ""
            )
            _conda_plat = conda_containers.get(plat)
            conda_plat: dict = _conda_plat if isinstance(_conda_plat, dict) else {}
            conda_lock = conda_plat.get("lock_file", "")
            if docker_build_id and conda_lock:
                docker_build_id_clean = docker_build_id[3:] if docker_build_id.startswith("bd-") else docker_build_id
                parts = docker_build_id_clean.split("_")
                if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
                    parts = parts[:-2]
                docker_hash = "_".join([p for p in parts if p])
                if docker_hash and docker_hash in conda_lock:
                    module.passed.append(
                        (
                            "meta_yml",
                            "containers_conda_lock_hash",
                            f"Conda lock_file matches docker {plat} buildId hash",
                            meta_path,
                        )
                    )
                else:
                    module.failed.append(
                        (
                            "meta_yml",
                            "containers_conda_lock_hash",
                            f"Conda lock_file does not match docker {plat} buildId hash",
                            meta_path,
                        )
                    )
            elif docker_build_id:
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_hash",
                        f"Could not compare conda lock_file with docker {plat} buildId hash",
                        meta_path,
                    )
                )
                break

            docker_build_id_clean = containers.docker[plat].build_id.lstrip("bd-")
            parts = docker_build_id_clean.split("_")
            if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
                parts = parts[:-2]
            docker_hash = "_".join([p for p in parts if p])
            if docker_hash and docker_hash in conda_lock:
                module.passed.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_hash",
                        f"Conda lock_file matches docker {plat} buildId hash",
                        meta_path,
                    )
                )
            else:
                module.failed.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_hash",
                        f"Conda lock_file does not match docker {plat} buildId hash",
                        meta_path,
                    )
                )
    return


def lint_main_nf_container(
    module: NFCoreComponent, fix=False, skip_docker=False, skip_conda=False, skip_singularity=False
):
    if module_uses_dockerfile(module):
        log.info(f"Module '{module.component_name}' uses a Dockerfile - skipping main.nf container lint")
        return

    if skip_docker:
        log.debug("Skipping main.nf container linting")
        return

    if not module.container_from_main_nf:
        log.debug("Skipping main.nf container linting")
        module.warned.append(
            ("main_nf", "has_container", "Module `main.nf` does not specify a container.", module.main_nf)
        )
        return

    main_path = Path(module.component_dir, "main.nf")
    meta_path = Path(module.component_dir, "meta.yml")

    meta_yml = module.load_meta_yml()
    if meta_yml is None:
        return
    try:
        docker_container_raw = meta_yml.get("containers", {}).get("docker", {}).get("linux/amd64", {})
        docker_container = MetaYmlContainers.DockerContainer.model_validate(docker_container_raw)
    except ValidationError as e:
        log.debug(f"Docker linux/amd64 image could not be read from {meta_path.absolute()}")
        log.debug(e)
        return

    if docker_container.name != module.container_from_main_nf:
        module.warned.append(
            (
                "main_nf",
                "main_nf_container",
                "Docker image in main.nf does not match the image specified in meta.yml",
                main_path,
            )
        )

        if fix:
            # TODO: Update main.nf container
            # update_main_nf_container(new_image)
            pass


def lint_conda_lock_files(module: NFCoreComponent):
    # TODO
    pass
