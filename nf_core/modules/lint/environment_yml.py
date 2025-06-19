import json
import logging
from pathlib import Path

import yaml
from jsonschema import exceptions, validators

from nf_core.components.lint import ComponentLint, LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.utils import custom_yaml_dumper

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
        with open(module.environment_yml) as fh:
            env_yml = yaml.safe_load(fh)

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
            # Check that the dependencies section is sorted alphabetically
            def sort_recursively(obj):
                """Simple recursive sort for nested structures."""
                if isinstance(obj, list):

                    def get_key(x):
                        if isinstance(x, dict):
                            # For dicts like {"pip": [...]}, use the key "pip"
                            return (list(x.keys())[0], 1)
                        else:
                            # For strings like "pip=23.3.1", use "pip" and for bioconda::samtools=1.15.1, use "bioconda::samtools"
                            return (str(x).split("=")[0], 0)

                    return sorted([sort_recursively(item) for item in obj], key=get_key)
                elif isinstance(obj, dict):
                    return {k: sort_recursively(v) for k, v in obj.items()}
                else:
                    return obj

            sorted_dependencies = sort_recursively(env_yml["dependencies"])

            # Direct comparison of sorted vs original dependencies
            if sorted_dependencies == env_yml["dependencies"]:
                module.passed.append(
                    (
                        "environment_yml_sorted",
                        "The dependencies in the module's `environment.yml` are sorted alphabetically",
                        module.environment_yml,
                    )
                )
            else:
                # sort it and write it back to the file
                log.info(
                    f"Dependencies in {module.component_name}'s environment.yml were not sorted alphabetically. Sorting them now."
                )
                env_yml["dependencies"] = sorted_dependencies
                with open(Path(module.component_dir, "environment.yml"), "w") as fh:
                    yaml.dump(env_yml, fh, Dumper=custom_yaml_dumper())
