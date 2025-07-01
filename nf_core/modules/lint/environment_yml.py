import json
import logging
from pathlib import Path

import yaml
from jsonschema import exceptions, validators

from nf_core.components.lint import ComponentLint, LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


def environment_yml(module_lint_object: ComponentLint, module: NFCoreComponent, allow_missing: bool = False) -> None:
    """
    Lint an ``environment.yml`` file.

    The lint test checks that the ``dependencies`` section
    in the environment.yml file is valid YAML and that it
    is sorted alphabetically.
    """
    env_yml = None
    #  load the environment.yml file
    if module.environment_yml is None:
        if allow_missing:
            module.warned.append(
                (
                    "environment_yml_exists",
                    "Module's `environment.yml` does not exist",
                    Path(module.component_dir, "environment.yml"),
                ),
            )
            return
        raise LintExceptionError("Module does not have an `environment.yml` file")
    try:
        # Read the entire file content to handle headers properly
        with open(module.environment_yml) as fh:
            lines = fh.readlines()

        # Define the schema lines to be added if missing
        schema_lines = [
            "---\n",
            "# yaml-language-server: $schema=https://raw.githubusercontent.com/nf-core/modules/master/modules/environment-schema.json\n",
        ]

        # Check if the first two lines match the expected schema lines
        if len(lines) >= 2 and lines[:2] == schema_lines:
            content = "".join(lines[2:])  # Skip schema lines when reading content
        else:
            content = "".join(lines)  # Use all content if no schema lines present

        # Parse the YAML content
        env_yml = yaml.safe_load(content)
        if env_yml is None:
            raise yaml.scanner.ScannerError("Empty YAML file")

        module.passed.append(("environment_yml_exists", "Module's `environment.yml` exists", module.environment_yml))

    except FileNotFoundError:
        # check if the module's main.nf requires a conda environment
        with open(Path(module.component_dir, "main.nf")) as fh:
            main_nf = fh.read()
            if 'conda "${moduleDir}/environment.yml"' in main_nf:
                module.failed.append(
                    ("environment_yml_exists", "Module's `environment.yml` does not exist", module.environment_yml)
                )
            else:
                module.passed.append(
                    (
                        "environment_yml_exists",
                        "Module's `environment.yml` does not exist, but it is also not included in the main.nf",
                        module.environment_yml,
                    )
                )

    # Confirm that the environment.yml file is valid according to the JSON schema
    if env_yml:
        valid_env_yml = False
        try:
            with open(Path(module_lint_object.modules_repo.local_repo_dir, "modules/environment-schema.json")) as fh:
                schema = json.load(fh)
            validators.validate(instance=env_yml, schema=schema)
            module.passed.append(
                ("environment_yml_valid", "Module's `environment.yml` is valid", module.environment_yml)
            )
            valid_env_yml = True
        except exceptions.ValidationError as e:
            hint = ""
            if len(e.path) > 0:
                hint = f"\nCheck the entry for `{e.path[0]}`."
            if e.schema and isinstance(e.schema, dict) and "message" in e.schema:
                e.message = e.schema["message"]
            module.failed.append(
                (
                    "environment_yml_valid",
                    f"The `environment.yml` of the module {module.component_name} is not valid: {e.message}.{hint}",
                    module.environment_yml,
                )
            )

        if valid_env_yml:
            # Define channel priority order
            channel_order = {
                "conda-forge": 0,
                "bioconda": 1,
            }

            # Sort dependencies if they exist
            if "dependencies" in env_yml:
                dicts = []
                others = []

                for term in env_yml["dependencies"]:
                    if isinstance(term, dict):
                        dicts.append(term)
                    else:
                        others.append(term)

                # Sort non-dict dependencies (strings) alphabetically
                others.sort(key=str)

                # Sort any lists within dict dependencies
                for dict_term in dicts:
                    for value in dict_term.values():
                        if isinstance(value, list):
                            value.sort(key=str)

                # Sort dict dependencies alphabetically
                dicts.sort(key=str)

                # Combine sorted dependencies
                sorted_deps = others + dicts

                # Check if dependencies are already sorted
                is_sorted = env_yml["dependencies"] == sorted_deps and all(
                    not isinstance(term, dict)
                    or all(not isinstance(value, list) or value == sorted(value, key=str) for value in term.values())
                    for term in env_yml["dependencies"]
                )
            else:
                sorted_deps = None
                is_sorted = True

            # Check if channels are sorted
            channels_sorted = True
            if "channels" in env_yml:
                sorted_channels = sorted(env_yml["channels"], key=lambda x: (channel_order.get(x, 2), str(x)))
                channels_sorted = env_yml["channels"] == sorted_channels

            if is_sorted and channels_sorted:
                module_lint_object.passed.append(
                    (
                        "environment_yml_sorted",
                        "The dependencies and channels in the module's `environment.yml` are sorted correctly",
                        module.environment_yml,
                    )
                )
            else:
                log.info(
                    f"Dependencies or channels in {module.component_name}'s environment.yml were not sorted. Sorting them now."
                )

                # Update dependencies if they need sorting
                if sorted_deps is not None:
                    env_yml["dependencies"] = sorted_deps

                # Update channels if they need sorting
                if "channels" in env_yml:
                    env_yml["channels"] = sorted(env_yml["channels"], key=lambda x: (channel_order.get(x, 2), str(x)))

                # Write back to file with headers
                with open(Path(module.component_dir, "environment.yml"), "w") as fh:
                    # Always write schema lines first
                    fh.writelines(schema_lines)
                    # Then dump the sorted YAML with proper formatting
                    yaml.dump(
                        env_yml,
                        fh,
                        default_flow_style=False,
                        indent=2,
                        sort_keys=False
                    )

                module_lint_object.passed.append(
                    (
                        "environment_yml_sorted",
                        "The dependencies and channels in the module's `environment.yml` have been sorted",
                        module.environment_yml,
                    )
                )
