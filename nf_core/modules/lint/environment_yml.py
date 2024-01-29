import json
import logging
from pathlib import Path

import yaml
from jsonschema import exceptions, validators

from nf_core.components.lint import ComponentLint
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.utils import custom_yaml_dumper

log = logging.getLogger(__name__)


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
        with open(Path(module.component_dir, "environment.yml")) as fh:
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
                        "The dependencies in the module's `environment.yml` are sorted alphabetically",
                        module.environment_yml,
                    )
                )
            else:
                # sort it and write it back to the file
                log.info(
                    f"Dependencies in {module.component_name}'s environment.yml were not sorted alphabetically. Sorting them now."
                )
                env_yml["dependencies"].sort()
                with open(Path(module.component_dir, "environment.yml"), "w") as fh:
                    yaml.dump(env_yml, fh, Dumper=custom_yaml_dumper())

            # Check that the name in the environment.yml file matches the name in the meta.yml file
            with open(Path(module.component_dir, "meta.yml")) as fh:
                meta_yml = yaml.safe_load(fh)

            if env_yml["name"] == meta_yml["name"]:
                module.passed.append(
                    (
                        "environment_yml_name",
                        "The module's `environment.yml` name matches module name",
                        module.environment_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "environment_yml_name",
                        f"Conflicting process name between environment.yml (`{env_yml['name']}`) and meta.yml (`{module.component_name}`)",
                        module.environment_yml,
                    )
                )

            # Check that the name is lowercase
            if env_yml["name"] == env_yml["name"].lower():
                module.passed.append(
                    (
                        "environment_yml_name_lowercase",
                        "The module's `environment.yml` name is lowercase",
                        module.environment_yml,
                    )
                )
            else:
                module.failed.append(
                    (
                        "environment_yml_name_lowercase",
                        "The module's `environment.yml` name is not lowercase",
                        module.environment_yml,
                    )
                )
