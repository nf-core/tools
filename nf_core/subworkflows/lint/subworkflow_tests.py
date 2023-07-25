"""
Lint the tests of a subworkflow in nf-core/modules
"""
import logging
import os

import yaml

log = logging.getLogger(__name__)


def subworkflow_tests(_, subworkflow):
    """
    Lint the tests of a subworkflow in ``nf-core/modules``

    It verifies that the test directory exists
    and contains a ``main.nf`` and a ``test.yml``,
    and that the subworkflow is present in the ``pytest_modules.yml``
    file.

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
            if subworkflow.component_name in pytest_yml.keys():
                subworkflow.passed.append(("test_pytest_yml", "correct entry in pytest_modules.yml", pytest_yml_path))
            else:
                subworkflow.failed.append(("test_pytest_yml", "missing entry in pytest_modules.yml", pytest_yml_path))
    except FileNotFoundError:
        subworkflow.failed.append(("test_pytest_yml", "Could not open pytest_modules.yml file", pytest_yml_path))

    # Lint the test.yml file
    try:
        with open(subworkflow.test_yml, "r") as fh:
            test_yml = yaml.safe_load(fh)

            # Verify that tags are correct
            all_tags_correct = True
            for test in test_yml:
                if not sorted(test["tags"]) == sorted([subworkflow.component_name, "subworkflows"]):
                    all_tags_correct = False

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

            if all_tags_correct:
                subworkflow.passed.append(("test_yml_tags", "tags adhere to guidelines", subworkflow.test_yml))
            else:
                subworkflow.failed.append(("test_yml_tags", "tags do not adhere to guidelines", subworkflow.test_yml))

        # Test that the file exists
        subworkflow.passed.append(("test_yml_exists", "Test `test.yml` exists", subworkflow.test_yml))
    except FileNotFoundError:
        subworkflow.failed.append(("test_yml_exists", "Test `test.yml` does not exist", subworkflow.test_yml))
