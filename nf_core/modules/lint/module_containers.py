import logging
from pathlib import Path

import requests
from pydantic_core import ValidationError

from nf_core.components.components_utils import read_meta_yml
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.modules_utils import MetaYmlContainers
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS

log = logging.getLogger(__name__)


def lint_meta_yml_containers(module: NFCoreComponent, skip_docker=False, skip_conda=False, skip_singularity=False):
    meta_path = Path(module.component_dir, "meta.yml")
    containers = module.container
    lock_keys = ("lock file", "lock_file", "lockFile", "lockfile")
    # Protocol and hash checks for docker/singularity
    skip_system = {"docker": skip_docker, "singularity": skip_singularity}
    for system in CONTAINER_SYSTEMS:
        if skip_system.get(system, False):
            continue
        # Check that the containers section contains entries for expected platforms
        sys_containers = containers.get(system, {})
        if not isinstance(sys_containers, dict):
            module.warned.append(
                ("meta_yml", "containers_section", f"Containers section missing '{system}' entries", meta_path)
            )
            continue
        platforms = [k for k in sys_containers if isinstance(sys_containers[k], dict) and k in CONTAINER_PLATFORMS]
        if not platforms:
            module.warned.append(
                (
                    "meta_yml",
                    "containers_section",
                    f"No {system} container entries found for expected platforms",
                    meta_path,
                )
            )
            continue
        for platform in platforms:
            # Check that each entry has specific fields and that it is not empty
            entry = sys_containers.get(platform, {})
            if not isinstance(entry, dict):
                entry = {}
            name = entry.get("name") or entry.get("image") or entry.get("container") or ""
            if not name:
                module.warned.append(
                    ("meta_yml", "containers_name", f"Missing {system} container name for {platform}", meta_path)
                )
                continue
            scheme = name.split("://", 1)[0].lower() if "://" in name else ""
            if system == "singularity":
                if scheme != "oras":
                    module.warned.append(
                        (
                            "meta_yml",
                            "containers_protocol",
                            f"Singularity container for {platform} should use 'oras://' protocol",
                            meta_path,
                        )
                    )
                else:
                    module.passed.append(
                        (
                            "meta_yml",
                            "containers_protocol",
                            f"Singularity container uses `oras` for {platform}",
                            meta_path,
                        )
                    )
            else:
                if scheme and scheme not in ("http", "https"):
                    module.warned.append(
                        (
                            "meta_yml",
                            "containers_protocol",
                            f"Docker container for {platform} should use http(s) or no protocol",
                            meta_path,
                        )
                    )
                else:
                    module.passed.append(
                        (
                            "meta_yml",
                            "containers_protocol",
                            f"Docker container uses `http/https` for {platform}",
                            meta_path,
                        )
                    )
            # check buildId hash matches hash in container tag
            build_id = entry.get("buildId") or entry.get("buildid") or entry.get("build_id") or ""
            if build_id:
                build_id_clean = build_id[3:] if build_id.startswith("bd-") else build_id
                parts = build_id_clean.split("_")
                build_hash = parts[0] if parts else ""

                name_no_scheme = name.split("://", 1)[1] if "://" in name else name
                if "@" in name_no_scheme:
                    name_no_scheme = name_no_scheme.split("@", 1)[0]
                if ":" not in name_no_scheme:
                    name_hash = ""
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
                                f"Build ID hash does not match {system} container tag for {platform}",
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
                            f"Could not compare build ID hash with {system} container tag for {platform}",
                            meta_path,
                        )
                    )
            else:
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_build_id_hash",
                        f"No buildId found for {system} {platform}",
                        meta_path,
                    )
                )

    # Check docker container images exist for all platforms (unless skipped)
    docker_containers = containers.get("docker", {})
    if not isinstance(docker_containers, dict):
        docker_containers = {}
    if not skip_docker:
        for platform in CONTAINER_PLATFORMS:
            docker_entry: dict = next(
                (
                    docker_containers[k]
                    for k in docker_containers
                    if platform == k and isinstance(docker_containers[k], dict)
                ),
                {},
            )
            docker_name = docker_entry.get("name") or docker_entry.get("image") or docker_entry.get("container") or ""
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
    conda_containers = containers.get("conda", {})
    if skip_conda:
        pass
    elif isinstance(conda_containers, dict) and conda_containers:
        conda_platforms = [
            k for k in conda_containers if isinstance(conda_containers[k], dict) and k in CONTAINER_PLATFORMS
        ]
        if not conda_platforms:
            module.warned.append(
                (
                    "meta_yml",
                    "containers_conda_lock_exists",
                    "No conda entries found for expected platforms",
                    meta_path,
                )
            )
        for platform in conda_platforms:
            entry = conda_containers.get(platform, {})
            if not isinstance(entry, dict):
                entry = {}
            lock_file: str | None = None
            for key in lock_keys:
                if entry.get(key):
                    lock_file = entry.get(key)
                    break
            if not lock_file:
                module.warned.append(
                    ("meta_yml", "containers_conda_lock_exists", f"Missing conda lock_file for {platform}", meta_path)
                )
                continue
            lock_path = Path(lock_file)
            if not lock_path.is_absolute():
                lock_path = module.component_dir / lock_path
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
            docker_plat: dict = (
                next(
                    (
                        docker_containers[k]
                        for k in docker_containers
                        if plat == k and isinstance(docker_containers[k], dict)
                    ),
                    {},
                )
                if isinstance(docker_containers, dict)
                else {}
            )
            docker_build_id = (
                docker_plat.get("buildId") or docker_plat.get("build_id") or docker_plat.get("buildid") or ""
            )
            conda_plat: dict = next(
                (conda_containers[k] for k in conda_containers if plat == k and isinstance(conda_containers[k], dict)),
                {},
            )
            conda_lock: str | None = None
            for key in lock_keys:
                if conda_plat.get(key):
                    conda_lock = conda_plat.get(key)
                    break
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
    else:
        module.warned.append(
            ("meta_yml", "containers_conda_lock_exists", "Conda containers section missing or empty", meta_path)
        )

    return


def lint_main_nf_container(
    module: NFCoreComponent, fix=False, skip_docker=False, skip_conda=False, skip_singularity=False
):
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

    meta_yml = read_meta_yml(meta_path)
    try:
        containers = MetaYmlContainers.model_validate(meta_yml.get("containers", {}))
        linux_amd = CONTAINER_PLATFORMS[0]
        meta_yml_docker_img = containers.docker.get(linux_amd).name  # type: ignore
    except (ValidationError, AttributeError) as e:
        log.debug(f"Docker {linux_amd} image could not be read from {meta_path.absolute()}")
        log.debug(e)
        return

    if meta_yml_docker_img != module.container_from_main_nf:
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
    env_path = Path(module.component_dir, "environment.yml")
    print(env_path)
    # TODO
