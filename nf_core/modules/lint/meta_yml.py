import json
import logging
from pathlib import Path
from typing import Union

import ruamel.yaml
from jsonschema import exceptions, validators

from nf_core.components.lint import ComponentLint, LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.modules_differ import ModulesDiffer

log = logging.getLogger(__name__)


def meta_yml(module_lint_object: ComponentLint, module: NFCoreComponent) -> None:
    """
    Lint a ``meta.yml`` file

    The lint test checks that the module has
    a ``meta.yml`` file and that it follows the
    JSON schema defined in the ``modules/meta-schema.json``
    file in the nf-core/modules repository.

    In addition it checks that the module name
    and module input is consistent between the
    ``meta.yml`` and the ``main.nf``.

    If the module has inputs or outputs, they are expected to be
    formatted as:

    .. code-block:: groovy

        tuple val(foo) path(bar)
        val foo
        path foo

    or permutations of the above.

    Args:
        module_lint_object (ComponentLint): The lint object for the module
        module (NFCoreComponent): The module to lint

    """

    # Check if we have a patch file, get original file in that case
    meta_yaml = read_meta_yml(module_lint_object, module)
    if module.is_patched and module_lint_object.modules_repo.repo_path is not None:
        lines = ModulesDiffer.try_apply_patch(
            module.component_name,
            module_lint_object.modules_repo.repo_path,
            module.patch_path,
            Path(module.component_dir).relative_to(module.base_dir),
            reverse=True,
        ).get("meta.yml")
        if lines is not None:
            yaml = ruamel.yaml.YAML()
            meta_yaml = yaml.safe_load("".join(lines))
    if module.meta_yml is None:
        raise LintExceptionError("Module does not have a `meta.yml` file")
    if meta_yaml is None:
        module.failed.append(("meta_yml_exists", "Module `meta.yml` does not exist", module.meta_yml))
        return
    else:
        module.passed.append(("meta_yml_exists", "Module `meta.yml` exists", module.meta_yml))

    # Confirm that the meta.yml file is valid according to the JSON schema
    valid_meta_yml = False
    try:
        with open(Path(module_lint_object.modules_repo.local_repo_dir, "modules/meta-schema.json")) as fh:
            schema = json.load(fh)
        validators.validate(instance=meta_yaml, schema=schema)
        module.passed.append(("meta_yml_valid", "Module `meta.yml` is valid", module.meta_yml))
        valid_meta_yml = True
    except exceptions.ValidationError as e:
        hint = ""
        if len(e.path) > 0:
            hint = f"\nCheck the entry for `{e.path[0]}`."
        if e.message.startswith("None is not of type 'object'") and len(e.path) > 2:
            hint = f"\nCheck that the child entries of {str(e.path[0])+'.'+str(e.path[2])} are indented correctly."
        if e.schema and isinstance(e.schema, dict) and "message" in e.schema:
            e.message = e.schema["message"]
            incorrect_value = meta_yaml
            for key in e.path:
                incorrect_value = incorrect_value[key]

            hint = hint + f"\nThe current value is `{incorrect_value}`."
        module.failed.append(
            (
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
                    "meta_name",
                    "Correct name specified in `meta.yml`.",
                    module.meta_yml,
                )
            )
        else:
            module.failed.append(
                (
                    "meta_name",
                    f"Conflicting `process` name between meta.yml (`{meta_yaml['name']}`) and main.nf (`{module.process_name}`)",
                    module.meta_yml,
                )
            )
        # Check that inputs are specified in meta.yml
        if len(module.inputs) > 0 and "input" not in meta_yaml:
            module.failed.append(
                (
                    "meta_input",
                    "Inputs not specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        elif len(module.inputs) > 0:
            module.passed.append(
                (
                    "meta_input",
                    "Inputs specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        else:
            log.debug(f"No inputs specified in module `main.nf`: {module.component_name}")
        # Check that all inputs are correctly specified
        if "input" in meta_yaml:
            correct_inputs, meta_inputs = obtain_correct_and_specified_inputs(module_lint_object, module, meta_yaml)

            if correct_inputs == meta_inputs:
                module.passed.append(
                    (
                        "correct_meta_inputs",
                        "Correct inputs specified in module `meta.yml`",
                        module.meta_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "correct_meta_inputs",
                        f"Module `meta.yml` does not match `main.nf`. Inputs should contain: {correct_inputs}\nRun `nf-core modules lint --fix` to update the `meta.yml` file.",
                        module.meta_yml,
                    )
                )

        # Check that outputs are specified in meta.yml
        if len(module.outputs) > 0 and "output" not in meta_yaml:
            module.failed.append(
                (
                    "meta_output",
                    "Outputs not specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        elif len(module.outputs) > 0:
            module.passed.append(
                (
                    "meta_output",
                    "Outputs specified in module `meta.yml`",
                    module.meta_yml,
                )
            )
        # Check that all outputs are correctly specified
        if "output" in meta_yaml:
            correct_outputs, meta_outputs = obtain_correct_and_specified_outputs(module_lint_object, module, meta_yaml)

            if correct_outputs == meta_outputs:
                module.passed.append(
                    (
                        "correct_meta_outputs",
                        "Correct outputs specified in module `meta.yml`",
                        module.meta_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "correct_meta_outputs",
                        f"Module `meta.yml` does not match `main.nf`. Outputs should contain: {correct_outputs}\nRun `nf-core modules lint --fix` to update the `meta.yml` file.",
                        module.meta_yml,
                    )
                )


def read_meta_yml(module_lint_object: ComponentLint, module: NFCoreComponent) -> Union[dict, None]:
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
        lines = ModulesDiffer.try_apply_patch(
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


def obtain_correct_and_specified_inputs(_, module, meta_yaml):
    """
    Obtain the list of correct inputs and the elements of each input channel.

    Args:
        module (object): The module object.
        meta_yaml (dict): The meta.yml dictionary.

    Returns:
        tuple: A tuple containing two lists. The first list contains the correct inputs,
               and the second list contains the inputs specified in meta.yml.
    """
    correct_inputs = []
    for input_channel in module.inputs:
        channel_elements = []
        for element in input_channel:
            channel_elements.append(list(element.keys())[0])
        correct_inputs.append(channel_elements)

    meta_inputs = []
    for input_channel in meta_yaml["input"]:
        if isinstance(input_channel, list):  # Correct format
            channel_elements = []
            for element in input_channel:
                channel_elements.append(list(element.keys())[0])
            meta_inputs.append(channel_elements)
        elif isinstance(input_channel, dict):  # Old format
            meta_inputs.append(list(input_channel.keys())[0])

    return correct_inputs, meta_inputs


def obtain_correct_and_specified_outputs(_, module, meta_yaml):
    """
    Obtain the dictionary of correct outputs and elements of each output channel.

    Args:
        module (object): The module object.
        meta_yaml (dict): The meta.yml dictionary.

    Returns:
        correct_outputs (dict): A dictionary containing the correct outputs and their elements.
        meta_outputs (dict): A dictionary containing the outputs specified in meta.yml.
    """
    correct_outputs = {}
    for output_channel in module.outputs:
        channel_name = list(output_channel.keys())[0]
        channel_elements = []
        for element in output_channel[channel_name]:
            channel_elements.append(list(element.keys())[0])
        correct_outputs[channel_name] = channel_elements

    meta_outputs = {}
    for output_channel in meta_yaml["output"]:
        channel_name = list(output_channel.keys())[0]
        if isinstance(output_channel[channel_name], list):  # Correct format
            channel_elements = []
            for element in output_channel[channel_name]:
                channel_elements.append(list(element.keys())[0])
            meta_outputs[channel_name] = channel_elements
        elif isinstance(output_channel[channel_name], dict):  # Old format
            meta_outputs[channel_name] = []

    return correct_outputs, meta_outputs
