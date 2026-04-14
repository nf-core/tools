"""
Lint the tests of a module in nf-core/modules
"""

import json
import logging
import re
from pathlib import Path

from nf_core.components.lint import LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


def module_tests(_, module: NFCoreComponent, allow_missing: bool = False):
    """Lint the tests of a module in ``nf-core/modules``

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

    * ``test_snap_versions``: The snapshot must contain a ``versions`` key.

    * ``test_main_tags``: The ``main.nf.test`` file must declare the required tags:
      ``modules``, ``modules_<org>``, the full component name, and (for ``tool/subtool``
      modules) the tool name alone. Tags for any chained components included via
      ``include`` statements must also be present.

    * ``test_old_test_dir``: The legacy pytest directory
      ``tests/modules/<component_name>/`` must not exist.

    """
    if module.nftest_testdir is None:
        if allow_missing:
            module.warned.append(
                (
                    "module_tests",
                    "test_dir_exists",
                    "nf-test directory is missing",
                    Path(module.component_dir, "tests"),
                )
            )
            return
        raise LintExceptionError("Module does not have a `tests` dir")

    if module.nftest_main_nf is None:
        if allow_missing:
            module.warned.append(
                (
                    "module_tests",
                    "test_main_nf_exists",
                    "test `main.nf.test` does not exist",
                    Path(module.component_dir, "tests", "main.nf.test"),
                )
            )
            return
        raise LintExceptionError("Module does not have a `tests` dir")

    repo_dir = module.component_dir.parts[: module.component_dir.parts.index(module.component_name.split("/")[0])][-1]
    test_dir = Path(module.base_dir, "tests", "modules", repo_dir, module.component_name)
    pytest_main_nf = Path(test_dir, "main.nf")
    is_pytest = pytest_main_nf.is_file()
    if module.nftest_testdir.is_dir():
        module.passed.append(
            ("module_tests", "test_dir_exists", "nf-test test directory exists", module.nftest_testdir)
        )
    else:
        if is_pytest:
            module.warned.append(
                (
                    "module_tests",
                    "test_dir_exists",
                    "nf-test directory is missing",
                    module.nftest_testdir,
                )
            )
        else:
            module.failed.append(
                (
                    "module_tests",
                    "test_dir_exists",
                    "nf-test directory is missing",
                    module.nftest_testdir,
                )
            )
        return

    # Lint the test main.nf file
    if module.nftest_main_nf.is_file():
        module.passed.append(
            ("module_tests", "test_main_nf_exists", "test `main.nf.test` exists", module.nftest_main_nf)
        )
    else:
        if is_pytest:
            module.warned.append(
                (
                    "module_tests",
                    "test_main_nf_exists",
                    "test `main.nf.test` does not exist",
                    module.nftest_main_nf,
                )
            )
        else:
            module.failed.append(
                (
                    "module_tests",
                    "test_main_nf_exists",
                    "test `main.nf.test` does not exist",
                    module.nftest_main_nf,
                )
            )

    if module.nftest_main_nf.is_file():
        # Check if main.nf.test.snap file exists, if 'snap(' is inside main.nf.test
        with open(module.nftest_main_nf) as fh:
            if "snapshot(" in fh.read():
                snap_file = module.nftest_testdir / "main.nf.test.snap"

                if snap_file.is_file():
                    module.passed.append(
                        (
                            "module_tests",
                            "test_snapshot_exists",
                            "snapshot file `main.nf.test.snap` exists",
                            snap_file,
                        )
                    )
                    # Validate no empty files
                    with open(snap_file) as snap_fh:
                        try:
                            snap_content = json.load(snap_fh)
                            for test_name in snap_content:
                                if "d41d8cd98f00b204e9800998ecf8427e" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
                                        module.failed.append(
                                            (
                                                "module_tests",
                                                "test_snap_md5sum",
                                                "md5sum for empty file found: d41d8cd98f00b204e9800998ecf8427e",
                                                snap_file,
                                            )
                                        )
                                    else:
                                        module.passed.append(
                                            (
                                                "module_tests",
                                                "test_snap_md5sum",
                                                "md5sum for empty file found, but it is a stub test",
                                                snap_file,
                                            )
                                        )
                                else:
                                    module.passed.append(
                                        (
                                            "module_tests",
                                            "test_snap_md5sum",
                                            "no md5sum for empty file found",
                                            snap_file,
                                        )
                                    )
                                if "7029066c27ac6f5ef18d660d5741979a" in str(snap_content[test_name]):
                                    if "stub" not in test_name:
                                        module.failed.append(
                                            (
                                                "module_tests",
                                                "test_snap_md5sum",
                                                "md5sum for compressed empty file found: 7029066c27ac6f5ef18d660d5741979a",
                                                snap_file,
                                            )
                                        )
                                    else:
                                        module.passed.append(
                                            (
                                                "module_tests",
                                                "test_snap_md5sum",
                                                "md5sum for compressed empty file found, but it is a stub test",
                                                snap_file,
                                            )
                                        )
                                else:
                                    module.passed.append(
                                        (
                                            "module_tests",
                                            "test_snap_md5sum",
                                            "no md5sum for compressed empty file found",
                                            snap_file,
                                        )
                                    )
                            if "versions" in str(snap_content[test_name]) or "versions" in str(snap_content.keys()):
                                module.passed.append(
                                    (
                                        "module_tests",
                                        "test_snap_versions",
                                        "versions found in snapshot file",
                                        snap_file,
                                    )
                                )
                            else:
                                module.failed.append(
                                    (
                                        "module_tests",
                                        "test_snap_versions",
                                        "versions not found in snapshot file",
                                        snap_file,
                                    )
                                )
                        except json.decoder.JSONDecodeError as e:
                            module.failed.append(
                                (
                                    "module_tests",
                                    "test_snapshot_exists",
                                    f"snapshot file `main.nf.test.snap` can't be read: {e}",
                                    snap_file,
                                )
                            )
                else:
                    module.failed.append(
                        (
                            "module_tests",
                            "test_snapshot_exists",
                            "snapshot file `main.nf.test.snap` does not exist",
                            snap_file,
                        )
                    )
            # Check that stub blocks with gzip files use proper syntax
            _check_stub_gzip_syntax(module)

            # Verify that tags are correct.
            main_nf_tags = module._get_main_nf_tags(module.nftest_main_nf)
            not_alphabet = re.compile(r"[^a-zA-Z]")
            org_alp = not_alphabet.sub("", module.org)
            org_alphabet = org_alp if org_alp != "" else "nfcore"
            required_tags = ["modules", f"modules_{org_alphabet}", module.component_name]
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
                module.passed.append(
                    (
                        "module_tests",
                        "test_main_tags",
                        "Tags adhere to guidelines",
                        module.nftest_main_nf,
                    )
                )
            else:
                module.failed.append(
                    (
                        "module_tests",
                        "test_main_tags",
                        f"Tags do not adhere to guidelines. Tags missing in `main.nf.test`: `{','.join(missing_tags)}`",
                        module.nftest_main_nf,
                    )
                )

    # Check that the old test directory does not exist
    if not is_pytest:
        old_test_dir = Path(module.base_dir, "tests", "modules", module.component_name)
        if old_test_dir.is_dir():
            module.failed.append(
                (
                    "module_tests",
                    "test_old_test_dir",
                    f"Pytest files are still present at `{Path('tests', 'modules', module.component_name)}`. Please remove this directory and its contents.",
                    old_test_dir,
                )
            )
        else:
            module.passed.append(
                (
                    "module_tests",
                    "test_old_test_dir",
                    "Old pytests don't exist for this module",
                    old_test_dir,
                )
            )


def _check_stub_gzip_syntax(module: NFCoreComponent):
    """
    Linting Checks perfomed:
    * ``test_stub_gzip_syntax``:
     Check that stub blocks with gzip output files use the proper syntax.
     Stub files ending in .gz must use: echo "" | gzip > file.gz
     Simply touching or creating empty .gz files will break nf-test's gzip parser
    """
    if not module.main_nf.is_file():
        return

    with open(module.main_nf) as fh:
        content = fh.read()

    # Find all stub blocks (matches both """ and ''' style strings)
    # Pattern matches: stub: followed by anything, then triple quotes, content, closing triple quotes
    stub_pattern = re.compile(r'stub:.*?(?:"""|\'\'\')\s*(.*?)\s*(?:"""|\'\'\')', re.DOTALL)
    stub_blocks = stub_pattern.findall(content)

    invalid_gz_patterns = []
    for stub_block in stub_blocks:
        # Look for lines that create .gz files
        # Only valid pattern is: echo "" | gzip > file.gz
        # Each .gz creation is always on a single line

        # Find all lines containing .gz in this stub block
        gz_lines = re.findall(r"^.*\.gz.*$", stub_block, re.MULTILINE)

        for line in gz_lines:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith(("//", "#")):
                continue

            # The ONLY valid pattern is: echo "" | gzip > file.gz
            valid_pattern = r'echo\s+""\s*\|\s*gzip\s*>\s*.*\.gz$'

            if not re.search(valid_pattern, line):
                invalid_gz_patterns.append(line.strip())

    if invalid_gz_patterns:
        module.failed.append(
            (
                "module_tests",
                "test_stub_gzip_syntax",
                f"Stub gzip files must use 'echo \"\" | gzip >' syntax. Invalid patterns found: {'; '.join(set(invalid_gz_patterns))}",
                module.main_nf,
            )
        )
    else:
        # Only add passed if there are actually stub blocks with .gz files
        if stub_blocks and any(".gz" in block for block in stub_blocks):
            module.passed.append(
                (
                    "module_tests",
                    "test_stub_gzip_syntax",
                    "Stub gzip files use correct syntax",
                    module.main_nf,
                )
            )
