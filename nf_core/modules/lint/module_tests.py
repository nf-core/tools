"""
Lint the tests of a module in nf-core/modules
"""
import os
import logging
import sys
import yaml

log = logging.getLogger(__name__)


def module_tests(module_lint_object, module):
    """
    Lint module tests
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

            if all_tags_correct:
                module.passed.append(("test_yml_tags", "tags adhere to guidelines", module.test_yml))
            else:
                module.failed.append(("test_yml_tags", "tags do not adhere to guidelines", module.test_yml))

        module.passed.append(("test_yml_exists", "Test `test.yml` exists", module.test_yml))
    except FileNotFoundError:
        module.failed.append(("test_yml_exists", "Test `test.yml` does not exist", module.test_yml))
