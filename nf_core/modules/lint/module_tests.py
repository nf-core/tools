"""
Lint the tests of a module in nf-core/modules
"""

import json
import logging
from pathlib import Path

import yaml

from nf_core.components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


def module_tests(_, module: NFCoreComponent):
    """
    Lint the tests of a module in ``nf-core/modules``

    It verifies that the test directory exists
    and contains a ``main.nf.test`` a ``main.nf.test.snap`` and ``tags.yml``.

    """
    repo_dir = module.component_dir.parts[: module.component_dir.parts.index(module.component_name.split("/")[0])][-1]
    test_dir = Path(module.base_dir, "tests", "modules", repo_dir, module.component_name)
    pytest_main_nf = Path(test_dir, "main.nf")
    is_pytest = pytest_main_nf.is_file()
    if module.nftest_testdir.is_dir():
        module.passed.append(("test_dir_exists", "nf-test test directory exists", module.nftest_testdir))
    else:
        if is_pytest:
            module.warned.append(("test_dir_exists", "nf-test directory is missing", module.nftest_testdir))
        else:
            module.failed.append(("test_dir_exists", "nf-test directory is missing", module.nftest_testdir))
        return

    # Lint the test main.nf file
    if module.nftest_main_nf.is_file():
        module.passed.append(("test_main_nf_exists", "test `main.nf.test` exists", module.nftest_main_nf))
    else:
        if is_pytest:
            module.warned.append(("test_main_nf_exists", "test `main.nf.test` does not exist", module.nftest_main_nf))
        else:
            module.failed.append(("test_main_nf_exists", "test `main.nf.test` does not exist", module.nftest_main_nf))

    if module.nftest_main_nf.is_file():
        # Check if main.nf.test.snap file exists, if 'snap(' is inside main.nf.test
        with open(module.nftest_main_nf) as fh:
            if "snapshot(" in fh.read():
                snap_file = module.nftest_testdir / "main.nf.test.snap"
                if snap_file.is_file():
                    module.passed.append(
                        ("test_snapshot_exists", "snapshot file `main.nf.test.snap` exists", snap_file)
                    )
                    # Validate no empty files
                    with open(snap_file) as snap_fh:
                        try:
                            snap_content = json.load(snap_fh)
                            for test_name in snap_content.keys():
                                if "d41d8cd98f00b204e9800998ecf8427e" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
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
                                                "md5sum for empty file found, but it is a stub test",
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
                                if "7029066c27ac6f5ef18d660d5741979a" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
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
                                                "md5sum for compressed empty file found, but it is a stub test",
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
                            if "versions" in str(snap_content[test_name]) or "versions" in str(snap_content.keys()):
                                module.passed.append(
                                    (
                                        "test_snap_versions",
                                        "versions found in snapshot file",
                                        snap_file,
                                    )
                                )
                            else:
                                module.failed.append(
                                    (
                                        "test_snap_versions",
                                        "versions not found in snapshot file",
                                        snap_file,
                                    )
                                )
                        except json.decoder.JSONDecodeError as e:
                            module.failed.append(
                                (
                                    "test_snapshot_exists",
                                    f"snapshot file `main.nf.test.snap` can't be read: {e}",
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
            chained_components_tags = module._get_included_components_in_chained_tests(module.nftest_main_nf)
            missing_tags = []
            log.debug(f"Required tags: {required_tags}")
            log.debug(f"Included components for chained nf-tests: {chained_components_tags}")
            for tag in set(required_tags + chained_components_tags):
                if tag not in main_nf_tags:
                    missing_tags.append(tag)
            if len(missing_tags) == 0:
                module.passed.append(("test_main_tags", "Tags adhere to guidelines", module.nftest_main_nf))
            else:
                module.failed.append(
                    (
                        "test_main_tags",
                        f"Tags do not adhere to guidelines. Tags missing in `main.nf.test`: `{','.join(missing_tags)}`",
                        module.nftest_main_nf,
                    )
                )

    # Check pytest_modules.yml does not contain entries for modules with nf-test
    pytest_yml_path = module.base_dir / "tests" / "config" / "pytest_modules.yml"
    if pytest_yml_path.is_file() and not is_pytest:
        try:
            with open(pytest_yml_path) as fh:
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
        with open(module.tags_yml) as fh:
            tags_yml = yaml.safe_load(fh)
            if module.component_name in tags_yml.keys():
                module.passed.append(("test_tags_yml", "correct entry in tags.yml", module.tags_yml))
                if f"modules/{module.org}/{module.component_name}/**" in tags_yml[module.component_name]:
                    module.passed.append(("test_tags_yml", "correct path in tags.yml", module.tags_yml))
                else:
                    module.failed.append(
                        (
                            "test_tags_yml",
                            f"incorrect path in tags.yml, expected `modules/{module.org}/{module.component_name}/**`, got `{tags_yml[module.component_name][0]}`",
                            module.tags_yml,
                        )
                    )
            else:
                module.failed.append(
                    (
                        "test_tags_yml",
                        f"incorrect key in tags.yml, should be `{module.component_name}`, got `{list(tags_yml.keys())[0]}`.",
                        module.tags_yml,
                    )
                )
    else:
        if is_pytest:
            module.warned.append(("test_tags_yml_exists", "file `tags.yml` does not exist", module.tags_yml))
        else:
            module.failed.append(("test_tags_yml_exists", "file `tags.yml` does not exist", module.tags_yml))

    # Check that the old test directory does not exist
    if not is_pytest:
        old_test_dir = Path(module.base_dir, "tests", "modules", module.component_name)
        if old_test_dir.is_dir():
            module.failed.append(
                (
                    "test_old_test_dir",
                    f"Pytest files are still present at `{Path('tests', 'modules', module.component_name)}`. Please remove this directory and its contents.",
                    old_test_dir,
                )
            )
        else:
            module.passed.append(("test_old_test_dir", "Old pytests don't exist for this module", old_test_dir))
