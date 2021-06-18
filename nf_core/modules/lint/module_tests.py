import os
import logging
import sys
import yaml

log = logging.getLogger(__name__)

def module_tests(self):
    """
    Lint module tests
    """

    if os.path.exists(self.test_dir):
        self.passed.append(("test_dir_exists", "Test directory exists", self.test_dir))
    else:
        self.failed.append(("test_dir_exists", "Test directory is missing", self.test_dir))
        return

    # Lint the test main.nf file
    test_main_nf = os.path.join(self.test_dir, "main.nf")
    if os.path.exists(test_main_nf):
        self.passed.append(("test_main_exists", "test `main.nf` exists", self.test_main_nf))
    else:
        self.failed.append(("test_main_exists", "test `main.nf` does not exist", self.test_main_nf))

    # Check that entry in pytest_software.yml exists
    try:
        pytest_yml_path = os.path.join(self.base_dir, "tests", "config", "pytest_software.yml")
        with open(pytest_yml_path, "r") as fh:
            pytest_yml = yaml.safe_load(fh)
            if self.module_name in pytest_yml.keys():
                self.passed.append(("test_pytest_yml", "correct entry in pytest_software.yml", pytest_yml_path))
            else:
                self.failed.append(("test_pytest_yml", "missing entry in pytest_software.yml", pytest_yml_path))
    except FileNotFoundError as e:
        log.error(f"Could not open pytest_software.yml file: {e}")
        sys.exit(1)

    # Lint the test.yml file
    try:
        with open(self.test_yml, "r") as fh:
            # TODO: verify that the tags are correct
            test_yml = yaml.safe_load(fh)

            # Verify that tags are correct
            all_tags_correct = True
            for test in test_yml:
                for tag in test["tags"]:
                    if not tag in [self.module_name, self.module_name.split("/")[0]]:
                        all_tags_correct = False

            if all_tags_correct:
                self.passed.append(("test_yml_tags", "tags adhere to guidelines", self.test_yml))
            else:
                self.failed.append(("test_yml_tags", "tags do not adhere to guidelines", self.test_yml))

        self.passed.append(("test_yml_exists", "Test `test.yml` exists", self.test_yml))
    except FileNotFoundError:
        self.failed.append(("test_yml_exists", "Test `test.yml` does not exist", self.test_yml))