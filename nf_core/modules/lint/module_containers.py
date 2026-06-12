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

    skip_system = {"docker": skip_docker, "singularity": skip_singularity, "conda": skip_conda}

    # Validate each container system separately with the pydantic model, so one
    # invalid system doesn't suppress the checks for the others. Lint messages
    # are derived from the collected validation errors.
    containers = MetaYmlContainers()
    for system_key in skip_system:
        if skip_system[system_key]:
            continue

        try:
            validated = MetaYmlContainers.model_validate(
                {system_key: containers_raw.get(system_key, {})},
                context={"require_complete": [system_key]},
            )
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(part) for part in err["loc"])
                module.failed.append(
                    ("meta_yml", f"containers_section_{system_key}", f"`{loc}`: {err['msg']}", meta_path)
                )
            continue

        setattr(containers, system_key, getattr(validated, system_key))
        module.passed.append(
            (
                "meta_yml",
                f"containers_section_{system_key}",
                f"{system_key} containers section is valid",
                meta_path,
            )
        )

        if system_key == "conda":
            continue

        # check build_id hash matches hash in container tag
        for platform, system in getattr(containers, system_key).items():
            if not system.build_id.removeprefix("bd-"):
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_build_id_hash",
                        f"No build_id found for {system_key} {platform}",
                        meta_path,
                    )
                )
                continue

            build_hash = system.build_hash
            name_hash = system.tag_hash
            if build_hash and name_hash:
                if build_hash != name_hash:
                    module.failed.append(
                        (
                            "meta_yml",
                            "containers_build_id_hash",
                            f"Build ID `{build_hash}` hash does not match {system_key} container tag `{name_hash}` for {platform}",
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
                # OCI distribution spec: /v2/<name>/manifests/<tag>
                host, _, image_ref = docker_name.partition("/")
                image_name, _, tag = image_ref.partition(":")
                docker_url = f"https://{host}/v2/{image_name}/manifests/{tag or 'latest'}"
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
                    response = requests.head(
                        docker_url,
                        allow_redirects=True,
                        headers={"Accept": "application/vnd.oci.image.manifest.v1+json"},
                    )
                    if response.ok or response.status_code == 401:
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
                                f"Docker {platform} image not reachable at {docker_url} (status {response.status_code})",
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
            conda_entry = containers.conda.get(plat)
            docker_entry = containers.docker.get(plat) if containers.docker else None
            conda_lock = conda_entry.lock_file if conda_entry else ""

            if not (docker_entry and docker_entry.build_id and conda_lock):
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_hash",
                        f"Could not compare conda lock_file with docker {plat} buildId hash",
                        meta_path,
                    )
                )
                continue

            docker_build_id_clean = docker_entry.build_id.removeprefix("bd-")
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
        docker_container = ContainerEntry.model_validate(docker_container_raw)
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
