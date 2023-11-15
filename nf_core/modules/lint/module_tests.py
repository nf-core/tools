"""
Lint the tests of a module in nf-core/modules
"""
import logging
import os

import yaml

log = logging.getLogger(__name__)


def module_tests(_, module):
    """
    Lint the tests of a module in ``nf-core/modules``

    It verifies that the test directory exists
    and contains a ``main.nf.test`` a ``main.nf.test.snap`` and ``tags.yml``.

    """
    if module.nftest_testdir.is_dir():
        module.passed.append(("test_dir_exists", "nf-test test directory exists", module.nftest_testdir))
    else:
        module.failed.append(("test_dir_exists", "nf-test directory is missing", module.nftest_testdir))
        return

    # Lint the test main.nf file
    if module.nftest_main_nf.is_file():
        module.passed.append(("test_main_exists", "test `main.nf.test` exists", module.nftest_main_nf))
    else:
        module.failed.append(("test_main_exists", "test `main.nf.test` does not exist", module.nftest_main_nf))

    if module.nftest_main_nf.is_file():
        # Check if main.nf.test.snap file exists, if 'snap(' is inside main.nf.test
        with open(module.nftest_main_nf, "r") as fh:
            if "snapshot(" in fh.read():
                snap_file = module.nftest_testdir / "main.nf.test.snap"
                if snap_file.is_file():
                    module.passed.append(
                        ("test_snapshot_exists", "snapshot file `main.nf.test.snap` exists", snap_file)
                    )
                    # Validate no empty files
                    with open(snap_file, "r") as snap_fh:
                        snap_content = snap_fh.read()
                        if "d41d8cd98f00b204e9800998ecf8427e" in snap_content:
                            module.failed.append(
                                (
                                    "test_snap_md5sum",
                                    "md5sum for empty file found: d41d8cd98f00b204e9800998ecf8427e",
                                    snap_file,
                                )
                            )
                        else:
                            module.passed.append(
                                (
                                    "test_snap_md5sum",
                                    "no md5sum for empty file found",
                                    snap_file,
                                )
                            )
                        if "7029066c27ac6f5ef18d660d5741979a" in snap_content:
                            module.failed.append(
                                (
                                    "test_snap_md5sum",
                                    "md5sum for compressed empty file found: 7029066c27ac6f5ef18d660d5741979a",
                                    snap_file,
                                )
                            )
                        else:
                            module.passed.append(
                                (
                                    "test_snap_md5sum",
                                    "no md5sum for compressed empty file found",
                                    snap_file,
                                )
                            )
                else:
                    module.failed.append(
                        ("test_snapshot_exists", "snapshot file `main.nf.test.snap` does not exist", snap_file)
                    )
            # Verify that tags are correct.
            main_nf_tags = module._get_main_nf_tags(module.nftest_main_nf)
            required_tags = ["modules", "modules_nfcore", module.component_name]
            if module.component_name.count("/") == 1:
                required_tags.append(module.component_name.split("/")[0])
            missing_tags = []
            for tag in required_tags:
                if tag not in main_nf_tags:
                    missing_tags.append(tag)
            if len(missing_tags) == 0:
                module.passed.append(("test_main_tags", "Tags adhere to guidelines", module.nftest_main_nf))
            else:
                module.failed.append(
                    (
                        "test_main_tags",
                        f"Tags do not adhere to guidelines. Tags missing in `main.nf.test`: {missing_tags}",
                        module.nftest_main_nf,
                    )
                )

    # Check pytest_modules.yml does not contain entries for subworkflows with nf-test
    pytest_yml_path = module.base_dir / "tests" / "config" / "pytest_modules.yml"
    if pytest_yml_path.is_file():
        try:
            with open(pytest_yml_path, "r") as fh:
                pytest_yml = yaml.safe_load(fh)
                if module.component_name in pytest_yml.keys():
                    module.failed.append(
                        (
                            "test_pytest_yml",
                            "module with nf-test should not be listed in pytest_modules.yml",
                            pytest_yml_path,
                        )
                    )
                else:
                    module.passed.append(
                        ("test_pytest_yml", "module with  nf-test not in pytest_modules.yml", pytest_yml_path)
                    )
        except FileNotFoundError:
            module.warned.append(("test_pytest_yml", "Could not open pytest_modules.yml file", pytest_yml_path))

    if module.tags_yml.is_file():
        # Check that tags.yml exists and it has the correct entry
        module.passed.append(("test_tags_yml_exists", "file `tags.yml` exists", module.tags_yml))
        with open(module.tags_yml, "r") as fh:
            tags_yml = yaml.safe_load(fh)
            if module.component_name in tags_yml.keys():
                module.passed.append(("test_tags_yml", "correct entry in tags.yml", module.tags_yml))
                if f"modules/{module.org}/{module.component_name}/**" in tags_yml[module.component_name]:
                    module.passed.append(("test_tags_yml", "correct path in tags.yml", module.tags_yml))
                else:
                    module.failed.append(("test_tags_yml", "incorrect path in tags.yml", module.tags_yml))
            else:
                module.failed.append(
                    (
                        "test_tags_yml",
                        "incorrect entry in tags.yml, should be '<TOOL>' or '<TOOL>/<SUBTOOL>'",
                        module.tags_yml,
                    )
                )
    else:
        module.failed.append(("test_tags_yml_exists", "file `tags.yml` does not exist", module.tags_yml))
