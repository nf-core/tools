import json
import logging
from pathlib import Path

import requests

from nf_core.components.components_utils import read_meta_yml
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, nextflow_inspect

log = logging.getLogger(__name__)


def lint_meta_yml_containers(module: NFCoreComponent, skip_docker=False, skip_conda=False, skip_singularity=False):
    meta_path = Path(module.component_dir, "meta.yml")
    containers = module.container
    platform_aliases = {p: (p, p.replace("/", "_")) for p in CONTAINER_PLATFORMS}
    lock_keys = ("lock file", "lock_file", "lockFile", "lockfile")
    # Protocol and hash checks for docker/singularity
    for system in CONTAINER_SYSTEMS:
        # Check that the containers section contains entries for expected platforms
        sys_containers = containers.get(system, {})
        if not isinstance(sys_containers, dict):
            module.warned.append(
                ("meta_yml", "containers_section", f"Containers section missing '{system}' entries", meta_path)
            )
            continue
        platforms = []
        for aliases in platform_aliases.values():
            for key in aliases:
                if isinstance(sys_containers.get(key), dict):
                    platforms.append(key)
                    break
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
                module.failed.append(
                    ("meta_yml", "containers_name", f"Missing {system} container name for {platform}", meta_path)
                )
                continue
            if "://" in name:
                scheme = name.split("://", 1)[0].lower()
            else:
                scheme = ""
            if system == "singularity":
                if scheme != "oras":
                    module.failed.append(
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
                            f"Singularity container protocol ok for {platform}",
                            meta_path,
                        )
                    )
            else:
                if scheme and scheme not in ("http", "https"):
                    module.failed.append(
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
                            f"Docker container protocol ok for {platform}",
                            meta_path,
                        )
                    )
            # check buildId hash matches hash in container tag
            build_id = entry.get("buildId") or entry.get("buildid") or entry.get("build_id") or ""
            if build_id:
                build_id_clean = build_id[3:] if build_id.startswith("bd-") else build_id
                parts = build_id_clean.split("_")
                build_hash = parts[0] if parts else ""

                if "://" in name:
                    name_no_scheme = name.split("://", 1)[1]
                else:
                    name_no_scheme = name
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

    # Check docker linux/amd64 image exists (unless skipped)
    skip_file = Path(module.base_dir, ".github", "skip_nf_test.json")
    with open(skip_file) as fh:
        data = json.load(fh)
    skip = set()
    for syst in CONTAINER_SYSTEMS + ["conda"]:
        value = data.get(syst)
        skip.update({x for x in value if isinstance(x, str)})
    module.passed.append(
        (
            "meta_yml",
            "containers_section",
            "Exceptions modules in nf-core/modules@master/.github/skip_nf_test.json ",
            meta_path,
        )
    )
    skip_modules = {x for x in skip if x.startswith(module.component_name + ":")}

    docker_containers = containers.get("docker", {})
    if isinstance(docker_containers, dict):
        docker_amd64 = docker_containers.get("linux/amd64", {})
        if not docker_amd64 or not isinstance(docker_amd64, dict):
            docker_amd64 = docker_containers.get("linux_amd64", {})
        if not isinstance(docker_amd64, dict):
            docker_amd64 = {}
    else:
        docker_amd64 = {}
    docker_amd64_name = docker_amd64.get("name") or docker_amd64.get("image") or docker_amd64.get("container") or ""

    if not docker_amd64_name:
        module.failed.append(
            (
                "meta_yml",
                "containers_docker_amd64_exists",
                "Docker linux/amd64 container name missing",
                meta_path,
            )
        )
    elif module.component_name not in skip_modules:
        if docker_amd64_name.startswith("http://") or docker_amd64_name.startswith("https://"):
            docker_url = docker_amd64_name
        elif "://" in docker_amd64_name:
            docker_url = ""
        else:
            docker_url = f"https://{docker_amd64_name}"
        if not docker_url:
            module.warned.append(
                (
                    "meta_yml",
                    "containers_docker_amd64_exists",
                    "Docker linux/amd64 container has non-http protocol; existence check skipped",
                    meta_path,
                )
            )
        else:
            try:
                response = requests.head(docker_url, stream=True, allow_redirects=True)
                if response.ok:
                    module.passed.append(
                        ("meta_yml", "containers_docker_amd64_exists", "Docker linux/amd64 image exists", meta_path)
                    )
                else:
                    module.failed.append(
                        (
                            "meta_yml",
                            "containers_docker_amd64_exists",
                            f"Docker linux/amd64 image not reachable (status {response.status_code})",
                            meta_path,
                        )
                    )
            except requests.RequestException as e:
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_docker_amd64_exists",
                        f"Unable to connect to docker image URL: {e}",
                        meta_path,
                    )
                )

    # Conda lock files and hash checks
    conda_containers = containers.get("conda", {})
    if isinstance(conda_containers, dict) and conda_containers:
        conda_platforms = []
        for aliases in platform_aliases.values():
            for key in aliases:
                if isinstance(conda_containers.get(key), dict):
                    conda_platforms.append(key)
                    break
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
                module.failed.append(
                    ("meta_yml", "containers_conda_lock_exists", f"Missing conda lock_file for {platform}", meta_path)
                )
                continue
            if lock_file.startswith("http://") or lock_file.startswith("https://"):
                module.warned.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_exists",
                        f"Conda lock_file for {platform} is remote; skipping local existence check",
                        meta_path,
                    )
                )
            else:
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
                    module.failed.append(
                        (
                            "meta_yml",
                            "containers_conda_lock_exists",
                            f"Conda lock_file not found for {platform}: {lock_path}",
                            meta_path,
                        )
                    )
        docker_build_id = (
            docker_amd64.get("buildId") or docker_amd64.get("build_id") or docker_amd64.get("buildid") or ""
        )
        conda_amd64 = conda_containers.get("linux/amd64", {})
        if not isinstance(conda_amd64, dict):
            conda_amd64 = conda_containers.get("linux_amd64", {})
        if not isinstance(conda_amd64, dict):
            conda_amd64 = {}
        conda_lock: str | None = None
        for key in lock_keys:
            if conda_amd64.get(key):
                conda_lock = conda_amd64.get(key)
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
                        "Conda lock_file matches docker linux/amd64 buildId hash",
                        meta_path,
                    )
                )
            else:
                module.failed.append(
                    (
                        "meta_yml",
                        "containers_conda_lock_hash",
                        "Conda lock_file does not match docker linux/amd64 buildId hash",
                        meta_path,
                    )
                )
        elif docker_build_id:
            module.warned.append(
                (
                    "meta_yml",
                    "containers_conda_lock_hash",
                    "Could not compare conda lock_file with docker linux/amd64 buildId hash",
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

    main_path = Path(module.component_dir, "main.nf")
    meta_path = Path(module.component_dir, "meta.yml")

    nf_insp_out = nextflow_inspect(main_path, format="json", profile="docker")
    main_nf_docker_img = nf_insp_out.get("processes", dict()).get("container")

    if main_nf_docker_img is None:
        log.debug("Docker image could not be extracted. Skipping container linting.")
        module.warned.append(("main_nf", "main_nf_container", "Docker container could not be extracted", main_path))
        return

    meta_yml = read_meta_yml(meta_path)
    meta_yml_docker_img = (
        meta_yml.get("containers", dict()).get("docker", dict()).get("linux_amd64", dict()).get("name", None)
    )

    if meta_yml_docker_img is None:
        log.debug(f"Docker linux_amd64 image could not be read from {meta_path.absolute()}")
        return

    if meta_yml_docker_img != main_nf_docker_img:
        module.failed.append(
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
