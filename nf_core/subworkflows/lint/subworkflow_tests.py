"""
Lint the tests of a subworkflow in nf-core/modules
"""

import json
import logging
import re
from pathlib import Path

from nf_core.components.lint import LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


def subworkflow_tests(_, subworkflow: NFCoreComponent, allow_missing: bool = False):
    """Lint the tests of a subworkflow in ``nf-core/modules``

    Checks the ``tests/`` directory and ``main.nf.test`` file for correctness,
    validates snapshot content, and verifies that nf-test tags follow guidelines.

    The following checks are performed:

    * ``test_dir_exists``: The nf-test directory ``tests/`` must exist.

    * ``test_main_nf_exists``: The file ``tests/main.nf.test`` must exist.

    * ``test_snapshot_exists``: If ``snapshot()`` is called in ``main.nf.test``,
      the snapshot file ``tests/main.nf.test.snap`` must exist and be valid JSON.

    * ``test_snap_md5sum``: The snapshot must not contain md5sums for empty files
      (``d41d8cd98f00b204e9800998ecf8427e``) or empty compressed files
      (``7029066c27ac6f5ef18d660d5741979a``), unless the test name contains ``stub``.

    * ``test_snap_versions``: The snapshot should contain a ``versions`` key.
      A warning (not a failure) is issued if it is absent, since subworkflows that
      use topic channels may not emit versions directly.

    * ``test_main_tags``: The ``main.nf.test`` file must declare the required tags:
      ``subworkflows``, ``subworkflows/<component_name>``, ``subworkflows_<org>``,
      all components included in the subworkflow's ``main.nf``, and any chained
      components referenced via ``include`` statements in the test file.

    * ``test_old_test_dir``: The legacy pytest directory
      ``tests/subworkflows/<component_name>/`` must not exist.

    """
    if subworkflow.nftest_testdir is None:
        if allow_missing:
            subworkflow.warned.append(
                (
                    "subworkflow_tests",
                    "test_dir_exists",
                    "nf-test directory is missing",
                    Path(subworkflow.component_dir, "tests"),
                )
            )
            return
        raise LintExceptionError("Module does not have a `tests` dir")

    if subworkflow.nftest_main_nf is None:
        if allow_missing:
            subworkflow.warned.append(
                (
                    "subworkflow_tests",
                    "test_main_nf_exists",
                    "test `main.nf.test` does not exist",
                    Path(subworkflow.component_dir, "tests", "main.nf.test"),
                )
            )
            return
        raise LintExceptionError("Subworkflow does not have a `tests` dir")

    repo_dir = subworkflow.component_dir.parts[
        : subworkflow.component_dir.parts.index(subworkflow.component_name.split("/")[0])
    ][-1]
    pytest_dir = Path(
        subworkflow.base_dir,
        "tests",
        "subworkflows",
        repo_dir,
        subworkflow.component_name,
    )
    pytest_main_nf = Path(pytest_dir, "main.nf")
    is_pytest = pytest_main_nf.is_file()
    log.debug(f"{pytest_main_nf} is pytest: {is_pytest}")
    if subworkflow.nftest_testdir.is_dir():
        subworkflow.passed.append(
            (
                "subworkflow_tests",
                "test_dir_exists",
                "nf-test test directory exists",
                subworkflow.nftest_testdir,
            )
        )
    else:
        if is_pytest:
            subworkflow.warned.append(
                (
                    "subworkflow_tests",
                    "test_dir_exists",
                    "Migrate pytest-workflow to nf-test",
                    subworkflow.nftest_testdir,
                )
            )
        else:
            subworkflow.failed.append(
                (
                    "subworkflow_tests",
                    "test_dir_exists",
                    "nf-test directory is missing",
                    subworkflow.nftest_testdir,
                )
            )
        return

    # Lint the test main.nf file
    if subworkflow.nftest_main_nf.is_file():
        subworkflow.passed.append(
            (
                "subworkflow_tests",
                "test_main_nf_exists",
                "test `main.nf.test` exists",
                subworkflow.nftest_main_nf,
            )
        )
    else:
        if is_pytest:
            subworkflow.warned.append(
                (
                    "subworkflow_tests",
                    "test_main_nf_exists",
                    "test `main.nf.test` does not exist",
                    subworkflow.nftest_main_nf,
                )
            )
        else:
            subworkflow.failed.append(
                (
                    "subworkflow_tests",
                    "test_main_nf_exists",
                    "test `main.nf.test` does not exist",
                    subworkflow.nftest_main_nf,
                )
            )

    if subworkflow.nftest_main_nf.is_file():
        with open(subworkflow.nftest_main_nf) as fh:
            # Check if main.nf.test.snap file exists, if 'snap(' is inside main.nf.test
            if "snapshot(" in fh.read():
                snap_file = subworkflow.nftest_testdir / "main.nf.test.snap"
                if snap_file.is_file():
                    subworkflow.passed.append(
                        (
                            "subworkflow_tests",
                            "test_snapshot_exists",
                            "test `main.nf.test.snap` exists",
                            snap_file,
                        )
                    )
                    # Validate no empty files
                    with open(snap_file) as snap_fh:
                        try:
                            snap_content = json.load(snap_fh)
                            for test_name in snap_content.keys():
                                if "d41d8cd98f00b204e9800998ecf8427e" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
                                        subworkflow.failed.append(
                                            (
                                                "subworkflow_tests",
                                                "test_snap_md5sum",
                                                "md5sum for empty file found: d41d8cd98f00b204e9800998ecf8427e",
                                                snap_file,
                                            )
                                        )
                                    else:
                                        subworkflow.passed.append(
                                            (
                                                "subworkflow_tests",
                                                "test_snap_md5sum",
                                                "md5sum for empty file found, but it is a stub test",
                                                snap_file,
                                            )
                                        )
                                else:
                                    subworkflow.passed.append(
                                        (
                                            "subworkflow_tests",
                                            "test_snap_md5sum",
                                            "no md5sum for empty file found",
                                            snap_file,
                                        )
                                    )
                                if "7029066c27ac6f5ef18d660d5741979a" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
                                        subworkflow.failed.append(
                                            (
                                                "subworkflow_tests",
                                                "test_snap_md5sum",
                                                "md5sum for compressed empty file found: 7029066c27ac6f5ef18d660d5741979a",
                                                snap_file,
                                            )
                                        )
                                    else:
                                        subworkflow.failed.append(
                                            (
                                                "subworkflow_tests",
                                                "test_snap_md5sum",
                                                "md5sum for compressed empty file found, but it is a stub test",
                                                snap_file,
                                            )
                                        )
                                else:
                                    subworkflow.passed.append(
                                        (
                                            "subworkflow_tests",
                                            "test_snap_md5sum",
                                            "no md5sum for compressed empty file found",
                                            snap_file,
                                        )
                                    )
                        except json.decoder.JSONDecodeError as e:
                            subworkflow.failed.append(
                                (
                                    "subworkflow_tests",
                                    "test_snapshot_exists",
                                    f"snapshot file `main.nf.test.snap` can't be read: {e}",
                                    snap_file,
                                )
                            )
                else:
                    subworkflow.failed.append(
                        (
                            "subworkflow_tests",
                            "test_snapshot_exists",
                            "test `main.nf.test.snap` does not exist",
                            snap_file,
                        )
                    )
            # Verify that tags are correct.
            main_nf_tags = subworkflow._get_main_nf_tags(subworkflow.nftest_main_nf)
            not_alphabet = re.compile(r"[^a-zA-Z]")
            org_alp = not_alphabet.sub("", subworkflow.org)
            org_alphabet = org_alp if org_alp != "" else "nfcore"
            required_tags = [
                "subworkflows",
                f"subworkflows/{subworkflow.component_name}",
                f"subworkflows_{org_alphabet}",
            ]
            included_components = []
            if subworkflow.main_nf is not None and Path(subworkflow.main_nf).is_file():
                included_components = subworkflow._get_included_components(subworkflow.main_nf)
            if subworkflow.nftest_main_nf is not None and subworkflow.nftest_main_nf.is_file():
                chained_components_tags = subworkflow._get_included_components_in_chained_tests(
                    subworkflow.nftest_main_nf
                )
            log.debug(f"Included components: {included_components}")
            log.debug(f"Required tags: {required_tags}")
            log.debug(f"Included components for chained nf-tests: {chained_components_tags}")
            missing_tags = []
            for tag in set(required_tags + included_components + chained_components_tags):
                if tag not in main_nf_tags:
                    missing_tags.append(tag)
            if len(missing_tags) == 0:
                subworkflow.passed.append(
                    (
                        "subworkflow_tests",
                        "test_main_tags",
                        "Tags adhere to guidelines",
                        subworkflow.nftest_main_nf,
                    )
                )
            else:
                subworkflow.failed.append(
                    (
                        "subworkflow_tests",
                        "test_main_tags",
                        f"Tags do not adhere to guidelines. Tags missing in `main.nf.test`: {missing_tags}",
                        subworkflow.nftest_main_nf,
                    )
                )

    # Check that the old test directory does not exist
    if not is_pytest:
        if pytest_dir.is_dir():
            subworkflow.failed.append(
                ("subworkflow_tests", "test_old_test_dir", "old test directory exists", pytest_dir)
            )
        else:
            subworkflow.passed.append(
                ("subworkflow_tests", "test_old_test_dir", "old test directory does not exist", pytest_dir)
            )
