import json
from pathlib import Path

import yaml

from nf_core.components.lint import ComponentLint
from nf_core.components.nfcore_component import NFCoreComponent


def environment_yml(module_lint_object: ComponentLint, module: NFCoreComponent):
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
        return

    # Check that the dependencies section is sorted alphabetically
    if env_yml:
        if "dependencies" in env_yml:
            if isinstance(env_yml["dependencies"], list):
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
            else:
                module.failed.append(
                    (
                        "environment_yml_valid",
                        "Module's `environment.yml` doesn't have a correctly formatted `dependencies` section, expecting an array",
                        module.environment_yml,
                    )
                )
        else:
            module.failed.append(
                (
                    "environment_yml_valid",
                    "Module's `environment.yml` doesn't contain the required `dependencies` section",
                    module.environment_yml,
                )
            )
