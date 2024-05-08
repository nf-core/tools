"""
Lint the tests of a subworkflow in nf-core/modules
"""

import json
import logging
from pathlib import Path

import yaml

from nf_core.components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


def subworkflow_tests(_, subworkflow: NFCoreComponent):
    """
    Lint the tests of a subworkflow in ``nf-core/modules``

    It verifies that the test directory exists
    and contains a ``main.nf.test`` a ``main.nf.test.snap`` and ``tags.yml``.

    Additionally, checks that all included components in test ``main.nf`` are specified in ``test.yml``
    """

    repo_dir = subworkflow.component_dir.parts[
        : subworkflow.component_dir.parts.index(subworkflow.component_name.split("/")[0])
    ][-1]
    test_dir = Path(subworkflow.base_dir, "tests", "subworkflows", repo_dir, subworkflow.component_name)
    pytest_main_nf = Path(test_dir, "main.nf")
    is_pytest = pytest_main_nf.is_file()
    log.debug(f"{pytest_main_nf} is pytest: {is_pytest}")
    if subworkflow.nftest_testdir.is_dir():
        subworkflow.passed.append(("test_dir_exists", "nf-test test directory exists", subworkflow.nftest_testdir))
    else:
        if is_pytest:
            subworkflow.warned.append(("test_dir_exists", "nf-test directory is missing", subworkflow.nftest_testdir))
        else:
            subworkflow.failed.append(("test_dir_exists", "nf-test directory is missing", subworkflow.nftest_testdir))
        return

    # Lint the test main.nf file
    if subworkflow.nftest_main_nf.is_file():
        subworkflow.passed.append(("test_main_nf_exists", "test `main.nf.test` exists", subworkflow.nftest_main_nf))
    else:
        if is_pytest:
            subworkflow.warned.append(
                ("test_main_nf_exists", "test `main.nf.test` does not exist", subworkflow.nftest_main_nf)
            )
        else:
            subworkflow.failed.append(
                ("test_main_nf_exists", "test `main.nf.test` does not exist", subworkflow.nftest_main_nf)
            )

    if subworkflow.nftest_main_nf.is_file():
        with open(subworkflow.nftest_main_nf) as fh:
            # Check if main.nf.test.snap file exists, if 'snap(' is inside main.nf.test
            if "snapshot(" in fh.read():
                snap_file = subworkflow.nftest_testdir / "main.nf.test.snap"
                if snap_file.is_file():
                    subworkflow.passed.append(("test_snapshot_exists", "test `main.nf.test.snap` exists", snap_file))
                    # Validate no empty files
                    with open(snap_file) as snap_fh:
                        try:
                            snap_content = json.load(snap_fh)
                            for test_name in snap_content.keys():
                                if "d41d8cd98f00b204e9800998ecf8427e" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
                                        subworkflow.failed.append(
                                            (
                                                "test_snap_md5sum",
                                                "md5sum for empty file found: d41d8cd98f00b204e9800998ecf8427e",
                                                snap_file,
                                            )
                                        )
                                    else:
                                        subworkflow.passed.append(
                                            (
                                                "test_snap_md5sum",
                                                "md5sum for empty file found, but it is a stub test",
                                                snap_file,
                                            )
                                        )
                                else:
                                    subworkflow.passed.append(
                                        (
                                            "test_snap_md5sum",
                                            "no md5sum for empty file found",
                                            snap_file,
                                        )
                                    )
                                if "7029066c27ac6f5ef18d660d5741979a" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
                                        subworkflow.failed.append(
                                            (
                                                "test_snap_md5sum",
                                                "md5sum for compressed empty file found: 7029066c27ac6f5ef18d660d5741979a",
                                                snap_file,
                                            )
                                        )
                                    else:
                                        subworkflow.failed.append(
                                            (
                                                "test_snap_md5sum",
                                                "md5sum for compressed empty file found, but it is a stub test",
                                                snap_file,
                                            )
                                        )
                                else:
                                    subworkflow.passed.append(
                                        (
                                            "test_snap_md5sum",
                                            "no md5sum for compressed empty file found",
                                            snap_file,
                                        )
                                    )
                            if "versions" in str(snap_content[test_name]) or "versions" in str(snap_content.keys()):
                                subworkflow.passed.append(
                                    (
                                        "test_snap_versions",
                                        "versions found in snapshot file",
                                        snap_file,
                                    )
                                )
                            else:
                                subworkflow.warned.append(
                                    (
                                        "test_snap_versions",
                                        "versions not found in snapshot file",
                                        snap_file,
                                    )
                                )
                        except json.decoder.JSONDecodeError as e:
                            subworkflow.failed.append(
                                (
                                    "test_snapshot_exists",
                                    f"snapshot file `main.nf.test.snap` can't be read: {e}",
                                    snap_file,
                                )
                            )
                else:
                    subworkflow.failed.append(
                        ("test_snapshot_exists", "test `main.nf.test.snap` does not exist", snap_file)
                    )
            # Verify that tags are correct.
            main_nf_tags = subworkflow._get_main_nf_tags(subworkflow.nftest_main_nf)
            required_tags = [
                "subworkflows",
                f"subworkflows/{subworkflow.component_name}",
                "subworkflows_nfcore",
            ]
            included_components = []
            if subworkflow.main_nf.is_file():
                included_components = subworkflow._get_included_components(subworkflow.main_nf)
            chained_components_tags = subworkflow._get_included_components_in_chained_tests(subworkflow.nftest_main_nf)
            log.debug(f"Included components: {included_components}")
            log.debug(f"Required tags: {required_tags}")
            log.debug(f"Included components for chained nf-tests: {chained_components_tags}")
            missing_tags = []
            for tag in set(required_tags + included_components + chained_components_tags):
                if tag not in main_nf_tags:
                    missing_tags.append(tag)
            if len(missing_tags) == 0:
                subworkflow.passed.append(("test_main_tags", "Tags adhere to guidelines", subworkflow.nftest_main_nf))
            else:
                subworkflow.failed.append(
                    (
                        "test_main_tags",
                        f"Tags do not adhere to guidelines. Tags missing in `main.nf.test`: {missing_tags}",
                        subworkflow.nftest_main_nf,
                    )
                )

    # Check pytest_modules.yml does not contain entries for subworkflows with nf-test
    pytest_yml_path = subworkflow.base_dir / "tests" / "config" / "pytest_modules.yml"
    if pytest_yml_path.is_file() and not is_pytest:
        try:
            with open(pytest_yml_path) as fh:
                pytest_yml = yaml.safe_load(fh)
                if "subworkflows/" + subworkflow.component_name in pytest_yml.keys():
                    subworkflow.failed.append(
                        (
                            "test_pytest_yml",
                            "subworkflow with nf-test should not be listed in pytest_modules.yml",
                            pytest_yml_path,
                        )
                    )
                else:
                    subworkflow.passed.append(
                        ("test_pytest_yml", "subworkflow with  nf-test not in pytest_modules.yml", pytest_yml_path)
                    )
        except FileNotFoundError:
            subworkflow.warned.append(("test_pytest_yml", "Could not open pytest_modules.yml file", pytest_yml_path))

    if subworkflow.tags_yml.is_file():
        # Check tags.yml exists and it has the correct entry
        subworkflow.passed.append(("test_tags_yml_exists", "file `tags.yml` exists", subworkflow.tags_yml))
        with open(subworkflow.tags_yml) as fh:
            tags_yml = yaml.safe_load(fh)
            if "subworkflows/" + subworkflow.component_name in tags_yml.keys():
                subworkflow.passed.append(("test_tags_yml", "correct entry in tags.yml", subworkflow.tags_yml))
                if (
                    f"subworkflows/{subworkflow.org}/{subworkflow.component_name}/**"
                    in tags_yml["subworkflows/" + subworkflow.component_name]
                ):
                    subworkflow.passed.append(("test_tags_yml", "correct path in tags.yml", subworkflow.tags_yml))
                else:
                    subworkflow.failed.append(("test_tags_yml", "incorrect path in tags.yml", subworkflow.tags_yml))
            else:
                subworkflow.failed.append(
                    (
                        "test_tags_yml",
                        "incorrect entry in tags.yml, should be 'subworkflows/<SUBWORKFLOW_NAME>'",
                        subworkflow.tags_yml,
                    )
                )
    else:
        if is_pytest:
            subworkflow.warned.append(("test_tags_yml_exists", "file `tags.yml` does not exist", subworkflow.tags_yml))
        else:
            subworkflow.failed.append(("test_tags_yml_exists", "file `tags.yml` does not exist", subworkflow.tags_yml))

    # Check that the old test directory does not exist
    if not is_pytest:
        old_test_dir = Path(subworkflow.base_dir, "tests", "subworkflows", subworkflow.component_name)
        if old_test_dir.is_dir():
            subworkflow.failed.append(("test_old_test_dir", "old test directory exists", old_test_dir))
        else:
            subworkflow.passed.append(("test_old_test_dir", "old test directory does not exist", old_test_dir))
