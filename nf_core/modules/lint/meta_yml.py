from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import ruamel.yaml
from jsonschema import exceptions, validators

from nf_core.components.components_differ import ComponentsDiffer
from nf_core.components.lint import ComponentLint, LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.utils import unquote

if TYPE_CHECKING:
    from nf_core.modules.lint import ModuleLint

log = logging.getLogger(__name__)


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
    for channel_name in outputs.keys():
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
    for name in topics.keys():
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
