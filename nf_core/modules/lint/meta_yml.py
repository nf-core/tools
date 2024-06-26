import json
from pathlib import Path

import yaml
from jsonschema import exceptions, validators

from nf_core.components.lint import ComponentLint
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.modules_differ import ModulesDiffer


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

    module.get_inputs_from_main_nf()
    module.get_outputs_from_main_nf()
    # Check if we have a patch file, get original file in that case
    meta_yaml = None
    if module.is_patched:
        lines = ModulesDiffer.try_apply_patch(
            module.component_name,
            module_lint_object.modules_repo.repo_path,
            module.patch_path,
            Path(module.component_dir).relative_to(module.base_dir),
            reverse=True,
        ).get("meta.yml")
        if lines is not None:
            meta_yaml = yaml.safe_load("".join(lines))
    if meta_yaml is None:
        try:
            with open(module.meta_yml) as fh:
                meta_yaml = yaml.safe_load(fh)
            module.passed.append(("meta_yml_exists", "Module `meta.yml` exists", module.meta_yml))
        except FileNotFoundError:
            module.failed.append(("meta_yml_exists", "Module `meta.yml` does not exist", module.meta_yml))
            return

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
        if e.schema.get("message"):
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

    # Confirm that all input and output channels are specified
    if valid_meta_yml:
        if "input" in meta_yaml:
            meta_input = [list(x.keys())[0] for x in meta_yaml["input"]]
            for input in module.inputs:
                if input in meta_input:
                    module.passed.append(("meta_input_main_only", f"`{input}` specified", module.meta_yml))
                else:
                    module.warned.append(
                        (
                            "meta_input_main_only",
                            f"`{input}` is present as an input in the `main.nf`, but missing in `meta.yml`",
                            module.meta_yml,
                        )
                    )
            # check if there are any inputs in meta.yml that are not in main.nf
            for input in meta_input:
                if input in module.inputs:
                    module.passed.append(
                        (
                            "meta_input_meta_only",
                            f"`{input}` is present as an input in `meta.yml` and `main.nf`",
                            module.meta_yml,
                        )
                    )
                else:
                    module.warned.append(
                        (
                            "meta_input_meta_only",
                            f"`{input}` is present as an input in `meta.yml` but not in `main.nf`",
                            module.meta_yml,
                        )
                    )

        if "output" in meta_yaml and meta_yaml["output"] is not None:
            meta_output = [list(x.keys())[0] for x in meta_yaml["output"]]
            for output in module.outputs:
                if output in meta_output:
                    module.passed.append(("meta_output_main_only", f"`{output}` specified", module.meta_yml))
                else:
                    module.warned.append(
                        (
                            "meta_output_main_only",
                            f"`{output}`  is present as an output in the `main.nf`, but missing in `meta.yml`",
                            module.meta_yml,
                        )
                    )
            # check if there are any outputs in meta.yml that are not in main.nf
            for output in meta_output:
                if output in module.outputs:
                    module.passed.append(
                        (
                            "meta_output_meta_only",
                            f"`{output}` is present as an output in `meta.yml` and `main.nf`",
                            module.meta_yml,
                        )
                    )
                elif output == "meta":
                    module.passed.append(
                        (
                            "meta_output_meta_only",
                            f"`{output}` is skipped for `meta.yml` outputs",
                            module.meta_yml,
                        )
                    )
                else:
                    module.warned.append(
                        (
                            "meta_output_meta_only",
                            f"`{output}` is present as an output in `meta.yml` but not in `main.nf`",
                            module.meta_yml,
                        )
                    )
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
