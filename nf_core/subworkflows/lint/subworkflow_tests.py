"""
Lint the tests of a subworkflow in nf-core/modules
"""
import logging
import os
from pathlib import Path

import yaml

import nf_core.subworkflows

log = logging.getLogger(__name__)


def subworkflow_tests(_, subworkflow):
    """
    Lint the tests of a subworkflow in ``nf-core/modules``

    It verifies that the test directory exists
    and contains a ``main.nf`` and a ``test.yml``,
    and that the subworkflow is present in the ``pytest_modules.yml``
    file.

    Additionally, hecks that all included components in test ``main.nf`` are specified in ``test.yml``
    """

    if os.path.exists(subworkflow.test_dir):
        subworkflow.passed.append(("test_dir_exists", "Test directory exists", subworkflow.test_dir))
    else:
        subworkflow.failed.append(("test_dir_exists", "Test directory is missing", subworkflow.test_dir))
        return

    # Lint the test main.nf file
    test_main_nf = os.path.join(subworkflow.test_dir, "main.nf")
    if os.path.exists(test_main_nf):
        subworkflow.passed.append(("test_main_exists", "test `main.nf` exists", subworkflow.test_main_nf))
    else:
        subworkflow.failed.append(("test_main_exists", "test `main.nf` does not exist", subworkflow.test_main_nf))

    # Check that entry in pytest_modules.yml exists
    try:
        pytest_yml_path = os.path.join(subworkflow.base_dir, "tests", "config", "pytest_modules.yml")
        with open(pytest_yml_path, "r") as fh:
            pytest_yml = yaml.safe_load(fh)
            if "subworkflows/" + subworkflow.component_name in pytest_yml.keys():
                subworkflow.passed.append(("test_pytest_yml", "correct entry in pytest_modules.yml", pytest_yml_path))
            else:
                subworkflow.failed.append(("test_pytest_yml", "missing entry in pytest_modules.yml", pytest_yml_path))
    except FileNotFoundError:
        subworkflow.failed.append(("test_pytest_yml", "Could not open pytest_modules.yml file", pytest_yml_path))

    # Lint the test.yml file
    try:
        with open(subworkflow.test_yml, "r") as fh:
            test_yml = yaml.safe_load(fh)

            # Verify that tags are correct. All included components in test main.nf should be specified in test.yml so pytests run for all of them
            included_components = nf_core.subworkflows.SubworkflowTestYmlBuilder.parse_module_tags(
                subworkflow, subworkflow.component_dir
            )
            for test in test_yml:
                for component in set(included_components):
                    if component in test["tags"]:
                        subworkflow.passed.append(
                            (
                                "test_yml_tags",
                                f"Included module/subworkflow `{component}` specified in `test.yml`",
                                subworkflow.test_yml,
                            )
                        )
                    else:
                        subworkflow.failed.append(
                            (
                                "test_yml_tags",
                                f"Included module/subworkflow `{component}` missing in `test.yml`",
                                subworkflow.test_yml,
                            )
                        )
                    if component.startswith("subworkflows/"):
                        included_components += nf_core.subworkflows.SubworkflowTestYmlBuilder.parse_module_tags(
                            _,
                            Path(subworkflow.component_dir).parent.joinpath(component.replace("subworkflows/", "")),
                        )
                        included_components = list(set(included_components))

                # Look for md5sums of empty files
                for tfile in test.get("files", []):
                    if tfile.get("md5sum") == "d41d8cd98f00b204e9800998ecf8427e":
                        subworkflow.failed.append(
                            (
                                "test_yml_md5sum",
                                "md5sum for empty file found: d41d8cd98f00b204e9800998ecf8427e",
                                subworkflow.test_yml,
                            )
                        )
                    else:
                        subworkflow.passed.append(
                            (
                                "test_yml_md5sum",
                                "no md5sum for empty file found",
                                subworkflow.test_yml,
                            )
                        )
                    if tfile.get("md5sum") == "7029066c27ac6f5ef18d660d5741979a":
                        subworkflow.failed.append(
                            (
                                "test_yml_md5sum",
                                "md5sum for compressed empty file found: 7029066c27ac6f5ef18d660d5741979a",
                                subworkflow.test_yml,
                            )
                        )
                    else:
                        subworkflow.passed.append(
                            (
                                "test_yml_md5sum",
                                "no md5sum for compressed empty file found",
                                subworkflow.test_yml,
                            )
                        )

        # Test that the file exists
        subworkflow.passed.append(("test_yml_exists", "Test `test.yml` exists", subworkflow.test_yml))
    except FileNotFoundError:
        subworkflow.failed.append(("test_yml_exists", "Test `test.yml` does not exist", subworkflow.test_yml))
        subworkflow.failed.append(("test_yml_exists", "Test `test.yml` does not exist", subworkflow.test_yml))
        subworkflow.failed.append(("test_yml_exists", "Test `test.yml` does not exist", subworkflow.test_yml))
