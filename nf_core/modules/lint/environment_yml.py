import json
from pathlib import Path

import yaml
from jsonschema import exceptions, validators

from nf_core.components.lint import ComponentLint
from nf_core.components.nfcore_component import NFCoreComponent


def environment_yml(module_lint_object: ComponentLint, module: NFCoreComponent) -> None:
    """
    Lint an ``environment.yml`` file.

    The lint test checks that the ``dependencies`` section
    in the environment.yml file is valid YAML and that it
    is sorted alphabetically.
    """
    env_yml = None
    #  load the environment.yml file
    try:
        with open(Path(module.component_dir, "environment.yml"), "r") as fh:
            env_yml = yaml.safe_load(fh)

        module.passed.append(("environment_yml_exists", "Module `environment.yml` exists", module.environment_yml))

    except FileNotFoundError:
        module.failed.append(
            ("environment_yml_exists", "Module `environment.yml` does not exist", module.environment_yml)
        )

    # Confirm that the environment.yml file is valid according to the JSON schema
    if env_yml:
        valid_env_yml = False
        try:
            with open(
                Path(module_lint_object.modules_repo.local_repo_dir, "modules/environment-schema.json"), "r"
            ) as fh:
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
            if e.schema.get("message"):
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
            if sorted(env_yml["dependencies"]) == env_yml["dependencies"]:
                module.passed.append(
                    (
                        "environment_yml_sorted",
                        "Module's `environment.yml` is sorted alphabetically",
                        module.environment_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "environment_yml_sorted",
                        "Module's `environment.yml` is not sorted alphabetically",
                        module.environment_yml,
                    )
                )
            # Check that the name in the environment.yml file matches the module name
            if env_yml["name"] == module.component_name:
                module.passed.append(
                    (
                        "environment_yml_name",
                        "Module's `environment.yml` name matches module name",
                        module.environment_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "environment_yml_name",
                        "Module's `environment.yml` name does not match module name",
                        module.environment_yml,
                    )
                )