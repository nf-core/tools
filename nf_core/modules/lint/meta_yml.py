from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import requests
import ruamel.yaml
from jsonschema import exceptions, validators

from nf_core.components.components_differ import ComponentsDiffer
from nf_core.components.lint import ComponentLint, LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, unquote

if TYPE_CHECKING:
    from nf_core.modules.lint import ModuleLint

log = logging.getLogger(__name__)


def meta_yml_containers(module: NFCoreComponent):
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


def meta_yml(module_lint_object: ModuleLint, module: NFCoreComponent, allow_missing: bool = False) -> None:
    """Lint a ``meta.yml`` file

    Checks that the module has a ``meta.yml`` file, that it is valid according
    to the nf-core JSON schema, and that its contents are consistent with
    ``main.nf``.

    The following checks are performed:

    * ``meta_yml_exists``: The ``meta.yml`` file must exist.

    * ``meta_yml_valid``: The ``meta.yml`` must be valid according to the JSON
      schema defined in ``modules/meta-schema.json`` in the nf-core/modules
      repository.

    * ``meta_name``: The ``name`` field in ``meta.yml`` must match (case-insensitive)
      the process name declared in ``main.nf``.

    * ``meta_input``: If ``main.nf`` declares inputs, they must be listed under
      the ``input:`` key in ``meta.yml``.

    * ``correct_meta_inputs``: The inputs listed in ``meta.yml`` must exactly
      match those parsed from ``main.nf``. Run ``nf-core modules lint --fix``
      to auto-correct.

    * ``meta_output``: If ``main.nf`` declares outputs, they must be listed under
      the ``output:`` key in ``meta.yml``.

    * ``correct_meta_outputs``: The outputs listed in ``meta.yml`` must exactly
      match those parsed from ``main.nf``. Run ``nf-core modules lint --fix``
      to auto-correct.

    * ``has_meta_topics``: If ``main.nf`` declares topics, ``meta.yml`` must
      also contain a non-empty ``topics:`` block. Run
      ``nf-core modules lint --fix`` to auto-correct.

    * ``correct_meta_topics``: The topics listed in ``meta.yml`` must exactly
      match those parsed from ``main.nf``. Run ``nf-core modules lint --fix``
      to auto-correct.

    If the module has inputs or outputs, they are expected to be formatted as:

    .. code-block:: groovy

        tuple val(foo) path(bar)
        val foo
        path foo

    or permutations of the above.

    """
    if module.meta_yml is None:
        if allow_missing:
            module.warned.append(
                (
                    "meta_yml",
                    "meta_yml_exists",
                    "Module `meta.yml` does not exist",
                    Path(module.component_dir, "meta.yml"),
                )
            )
            return
        raise LintExceptionError("Module does not have a `meta.yml` file")
    # Check if we have a patch file, get original file in that case
    meta_yaml = read_meta_yml(module_lint_object, module)
    if module.is_patched and module_lint_object.modules_repo.repo_path is not None:
        lines = ComponentsDiffer.try_apply_patch(
            module.component_type,
            module.component_name,
            module_lint_object.modules_repo.repo_path,
            module.patch_path,
            Path(module.component_dir).relative_to(module.base_dir),
            reverse=True,
        ).get("meta.yml")
        if lines is not None:
            yaml = ruamel.yaml.YAML()
            meta_yaml = yaml.load("".join(lines))
    if meta_yaml is None:
        module.failed.append(("meta_yml", "meta_yml_exists", "Module `meta.yml` does not exist.", module.meta_yml))
        return
    else:
        module.passed.append(("meta_yml", "meta_yml_exists", "Module `meta.yml` exists", module.meta_yml))
    module.container = meta_yaml.get("containers", {})

    # Confirm that the meta.yml file is valid according to the JSON schema
    valid_meta_yml = False
    try:
        schema = module_lint_object.load_meta_schema()
        validators.validate(instance=meta_yaml, schema=schema)
        module.passed.append(("meta_yml", "meta_yml_valid", "Module `meta.yml` is valid", module.meta_yml))
        valid_meta_yml = True
    except exceptions.ValidationError as e:
        hint = ""
        if len(e.path) > 0:
            hint = f"\nCheck the entry for `{e.path}`."
        if e.message.startswith("None is not of type 'object'") and len(e.path) > 2:
            hint = f"\nCheck that the child entries of {str(e.path[0]) + '.' + str(e.path[2])} are indented correctly."
        if e.schema and isinstance(e.schema, dict) and "message" in e.schema:
            e.message = e.schema["message"]
            incorrect_value = meta_yaml
            for key in e.path:
                incorrect_value = incorrect_value[key]

            hint = hint + f"\nThe current value is `{incorrect_value}`."
        module.failed.append(
            (
                "meta_yml",
                "meta_yml_valid",
                f"The `meta.yml` of the module {module.component_name} is not valid: {e.message}.{hint}",
                module.meta_yml,
            )
        )

    # Confirm that all input and output channels are correctly specified
    if valid_meta_yml:
        # confirm that the name matches the process name in main.nf
        if meta_yaml["name"].upper() == module.process_name:
            module.passed.append(
                (
                    "meta_yml",
                    "meta_name",
                    "Correct name specified in `meta.yml`.",
                    module.meta_yml,
                )
            )
        else:
            module.failed.append(
                (
                    "meta_yml",
                    "meta_name",
                    f"Conflicting `process` name between meta.yml (`{meta_yaml['name']}`) and main.nf (`{module.process_name}`)",
                    module.meta_yml,
                )
            )
        # Check that inputs are specified in meta.yml
        if len(module.inputs) > 0 and "input" not in meta_yaml:
            module.failed.append(
                (
                    "meta_yml",
                    "meta_input",
                    "Inputs not specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        elif len(module.inputs) > 0:
            module.passed.append(
                (
                    "meta_yml",
                    "meta_input",
                    "Inputs specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        else:
            log.debug(f"No inputs specified in module `main.nf`: {module.component_name}")
        # Check that all inputs are correctly specified
        if "input" in meta_yaml:
            correct_inputs = obtain_inputs(module_lint_object, module.inputs)
            meta_inputs = obtain_inputs(module_lint_object, meta_yaml["input"])

            if correct_inputs == meta_inputs:
                module.passed.append(
                    (
                        "meta_yml",
                        "correct_meta_inputs",
                        "Correct inputs specified in module `meta.yml`",
                        module.meta_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "meta_yml",
                        "correct_meta_inputs",
                        f"Module `meta.yml` does not match `main.nf`. Inputs should contain: {correct_inputs}\nRun `nf-core modules lint --fix` to update the `meta.yml` file.",
                        module.meta_yml,
                    )
                )

        # Check that outputs are specified in meta.yml
        if len(module.outputs) > 0 and "output" not in meta_yaml:
            module.failed.append(
                (
                    "meta_yml",
                    "meta_output",
                    "Outputs not specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        elif len(module.outputs) > 0:
            module.passed.append(
                (
                    "meta_yml",
                    "meta_output",
                    "Outputs specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        # Check that all outputs are correctly specified
        if "output" in meta_yaml:
            correct_outputs = obtain_outputs(module_lint_object, module.outputs)
            meta_outputs = obtain_outputs(module_lint_object, meta_yaml["output"])
            log.debug(f"Correct outputs: {correct_outputs}")
            log.debug(f"Outputs in `meta.yml`: {meta_outputs}")
            if correct_outputs == meta_outputs:
                module.passed.append(
                    (
                        "meta_yml",
                        "correct_meta_outputs",
                        "Correct outputs specified in module `meta.yml`",
                        module.meta_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "meta_yml",
                        "correct_meta_outputs",
                        f"Module `meta.yml` does not match `main.nf`. Outputs should contain: {correct_outputs}\nRun `nf-core modules lint --fix` to update the `meta.yml` file.",
                        module.meta_yml,
                    )
                )
        # Check that all topics are correctly specified
        if "topics" in meta_yaml or module.topics:
            correct_topics = obtain_topics(module_lint_object, module.topics)
            meta_topics = obtain_topics(module_lint_object, meta_yaml.get("topics", {}))

            if not meta_topics:
                module.failed.append(
                    (
                        "meta_yml",
                        "has_meta_topics",
                        f"Module `meta.yml` does not contain any topics, even though they appear in `main.nf`. Use `nf-core modules lint {module.component_name} --fix` to automatically resolve this.",
                        module.meta_yml,
                    )
                )
                return
            else:
                module.passed.append(
                    (
                        "meta_yml",
                        "has_meta_topics",
                        "Module `meta.yml` and `main.nf` contain topics.",
                        module.meta_yml,
                    )
                )

            if correct_topics == meta_topics:
                module.passed.append(
                    (
                        "meta_yml",
                        "correct_meta_topics",
                        "Correct topics specified in module `meta.yml`",
                        module.meta_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "meta_yml",
                        "correct_meta_topics",
                        f"Module `meta.yml` does not match `main.nf`. Topics should contain: {correct_topics}\nRun `nf-core modules lint --fix` to update the `meta.yml` file.",
                        module.meta_yml,
                    )
                )

        # Check that all containers are correctly specified
        if "containers" in meta_yaml or module.container:
            correct_containers = obtain_containers(module_lint_object, module.container)
            meta_containers = obtain_containers(module_lint_object, meta_yaml.get("containers", {}))
            if not meta_containers:
                module.failed.append(
                    (
                        "meta_yml",
                        "has_meta_containers",
                        f"Module `meta.yml` does not contain any containers, even though they appear in `main.nf`. Use `nf-core modules lint {module.component_name} --fix` to automatically resolve this.",
                        module.meta_yml,
                    )
                )
                return
            else:
                module.passed.append(
                    (
                        "meta_yml",
                        "has_meta_containers",
                        "Module `meta.yml` and `main.nf` contain containers.",
                        module.meta_yml,
                    )
                )

            if correct_containers == meta_containers:
                module.passed.append(
                    (
                        "meta_yml",
                        "correct_meta_containers",
                        "Correct containers specified in module `meta.yml`",
                        module.meta_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "meta_yml",
                        "correct_meta_containers",
                        f"Module `meta.yml` does not match `main.nf`. Containers should contain: {correct_containers}\nRun `nf-core modules lint --fix` to update the `meta.yml` file.",
                        module.meta_yml,
                    )
                )

        _ = meta_yml_containers(module)


def read_meta_yml(module_lint_object: ComponentLint, module: NFCoreComponent) -> dict | None:
    """
    Read a `meta.yml` file and return it as a dictionary

    Args:
        module_lint_object (ComponentLint): The lint object for the module
        module (NFCoreComponent): The module to read

    Returns:
        dict: The `meta.yml` file as a dictionary
    """
    meta_yaml = None
    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    # Check if we have a patch file, get original file in that case
    if module.is_patched:
        lines = ComponentsDiffer.try_apply_patch(
            module.component_type,
            module.component_name,
            module_lint_object.modules_repo.repo_path,
            module.patch_path,
            Path(module.component_dir).relative_to(module.base_dir),
            reverse=True,
        ).get("meta.yml")
        if lines is not None:
            meta_yaml = yaml.load("".join(lines))
    if meta_yaml is None:
        if module.meta_yml is None:
            return None
        with open(module.meta_yml) as fh:
            meta_yaml = yaml.load(fh)
    return meta_yaml


def obtain_inputs(_, inputs: list) -> list:
    """
    Obtain the list of inputs and the elements of each input channel.

    Args:
        inputs (dict): The dictionary of inputs from main.nf or meta.yml files.

    Returns:
        formatted_inputs (dict): A dictionary containing the inputs and their elements obtained from main.nf or meta.yml files.
    """
    formatted_inputs: list[list[str] | str] = []
    for input_channel in inputs:
        if isinstance(input_channel, list):
            channel_elements = []
            for element in input_channel:
                key = list(element.keys())[0]
                channel_elements.append(unquote(key))
            formatted_inputs.append(channel_elements)
        else:
            key = list(input_channel.keys())[0]
            formatted_inputs.append(unquote(key))

    return formatted_inputs


def obtain_outputs(_, outputs: dict | list) -> dict | list:
    """
    Obtain the dictionary of outputs and elements of each output channel.

    Args:
        outputs (dict): The dictionary of outputs from main.nf or meta.yml files.

    Returns:
        formatted_outputs (dict): A dictionary containing the outputs and their elements obtained from main.nf or meta.yml files.
    """
    formatted_outputs: dict = {}
    old_structure = isinstance(outputs, list)
    if old_structure:
        outputs = {k: v for d in outputs for k, v in d.items()}
    assert isinstance(outputs, dict)  # mypy
    for channel_name in outputs:
        output_channel = outputs[channel_name]
        channel_elements: list = []
        for element in output_channel:
            if isinstance(element, list):
                channel_elements.append([])
                for e in element:
                    key = list(e.keys())[0]
                    channel_elements[-1].append(unquote(key))
            else:
                key = list(element.keys())[0]
                channel_elements.append(unquote(key))
        formatted_outputs[channel_name] = channel_elements

    if old_structure:
        return [{k: v} for k, v in formatted_outputs.items()]
    else:
        return formatted_outputs


def obtain_topics(_, topics: dict) -> dict:
    """
    Obtain the dictionary of topics and elements of each topic.

    Args:
        topics (dict): The dictionary of topics from main.nf or meta.yml files.

    Returns:
        formatted_topics (dict): A dictionary containing the topics and their elements obtained from main.nf or meta.yml files.
    """
    formatted_topics: dict = {}
    for name in topics:
        content = topics[name]
        t_elements: list = []
        for element in content:
            if isinstance(element, list):
                t_elements.append([])
                for e in element:
                    key = list(e.keys())[0]
                    t_elements[-1].append(unquote(key))
            else:
                key = list(element.keys())[0]
                t_elements.append(unquote(key))
        formatted_topics[name] = t_elements

    return formatted_topics


def obtain_containers(_, containers: dict) -> dict:
    """
    Obtain the dictionary of containers and their elements.

    Args:
        containers (dict): The dictionary of containers from meta.yml files.

    Returns:
        formatted_containers (dict): A dictionary containing the containers and their elements obtained from meta.yml files.
    """
    formatted_containers: dict = {}
    for system in containers.keys():
        sys_containers = containers[system]
        platform_dict: dict = {}
        for platform in sys_containers.keys():
            entry = sys_containers[platform]
            platform_dict[platform] = entry
        formatted_containers[system] = platform_dict

    return formatted_containers
