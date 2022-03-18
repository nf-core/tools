"""
Lint the tests of a module in nf-core/modules
"""
import os
import logging
import yaml

log = logging.getLogger(__name__)


def module_tests(module_lint_object, module):
    """
    Lint the tests of a module in ``nf-core/modules``

    It verifies that the test directory exists
    and contains a ``main.nf`` and a ``test.yml``,
    and that the module is present in the ``pytest_modules.yml``
    file.

    """

    if os.path.exists(module.test_dir):
        module.passed.append(("test_dir_exists", "Test directory exists", module.test_dir))
    else:
        module.failed.append(("test_dir_exists", "Test directory is missing", module.test_dir))
        return

    # Lint the test main.nf file
    test_main_nf = os.path.join(module.test_dir, "main.nf")
    if os.path.exists(test_main_nf):
        module.passed.append(("test_main_exists", "test `main.nf` exists", module.test_main_nf))
    else:
        module.failed.append(("test_main_exists", "test `main.nf` does not exist", module.test_main_nf))

    # Check that entry in pytest_modules.yml exists
    try:
        pytest_yml_path = os.path.join(module.base_dir, "tests", "config", "pytest_modules.yml")
        with open(pytest_yml_path, "r") as fh:
            pytest_yml = yaml.safe_load(fh)
            if module.module_name in pytest_yml.keys():
                module.passed.append(("test_pytest_yml", "correct entry in pytest_modules.yml", pytest_yml_path))
            else:
                module.failed.append(("test_pytest_yml", "missing entry in pytest_modules.yml", pytest_yml_path))
    except FileNotFoundError as e:
        module.failed.append(("test_pytest_yml", f"Could not open pytest_modules.yml file", pytest_yml_path))

    # Lint the test.yml file
    try:
        with open(module.test_yml, "r") as fh:
            # TODO: verify that the tags are correct
            test_yml = yaml.safe_load(fh)

            # Verify that tags are correct
            all_tags_correct = True
            for test in test_yml:
                for tag in test["tags"]:
                    if not tag in [module.module_name, module.module_name.split("/")[0]]:
                        all_tags_correct = False

                # Look for md5sums of empty files
                for tfile in test.get("files", []):
                    if tfile.get("md5sum") == "d41d8cd98f00b204e9800998ecf8427e":
                        module.failed.append(
                            (
                                "test_yml_md5sum",
                                "md5sum for empty file found: d41d8cd98f00b204e9800998ecf8427e",
                                module.test_yml,
                            )
                        )
                    if tfile.get("md5sum") == "7029066c27ac6f5ef18d660d5741979a":
                        module.failed.append(
                            (
                                "test_yml_md5sum",
                                "md5sum for compressed empty file found: 7029066c27ac6f5ef18d660d5741979a",
                                module.test_yml,
                            )
                        )

            if all_tags_correct:
                module.passed.append(("test_yml_tags", "tags adhere to guidelines", module.test_yml))
            else:
                module.failed.append(("test_yml_tags", "tags do not adhere to guidelines", module.test_yml))

        # Test that the file exists
        module.passed.append(("test_yml_exists", "Test `test.yml` exists", module.test_yml))
    except FileNotFoundError:
        module.failed.append(("test_yml_exists", "Test `test.yml` does not exist", module.test_yml))
