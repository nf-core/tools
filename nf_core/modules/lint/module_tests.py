"""
Lint the tests of a module in nf-core/modules
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

import yaml

from nf_core.components.lint import LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


class ModuleTestValidator:
    """Base class for module test validators with common result handling."""

    def __init__(self, module: NFCoreComponent):
        self.module = module

    def add_passed(self, test_name: str, message: str, file_path: Optional[Path] = None):
        """Add a passed test result."""
        file_path = file_path or self.module.nftest_testdir or Path(self.module.component_dir)
        self.module.passed.append((test_name, message, file_path))

    def add_failed(self, test_name: str, message: str, file_path: Optional[Path] = None):
        """Add a failed test result."""
        file_path = file_path or self.module.nftest_testdir or Path(self.module.component_dir)
        self.module.failed.append((test_name, message, file_path))

    def add_warned(self, test_name: str, message: str, file_path: Optional[Path] = None):
        """Add a warned test result."""
        file_path = file_path or self.module.nftest_testdir or Path(self.module.component_dir)
        self.module.warned.append((test_name, message, file_path))

    def validate(self) -> bool:
        """Run validation. Return True if validation should continue, False to stop."""
        raise NotImplementedError("Subclasses must implement validate()")


class TestDirectoryValidator(ModuleTestValidator):
    """Validates test directory structure and basic file existence."""

    def validate(self) -> bool:
        """Validate test directory and main.nf.test file existence."""
        if self.module.nftest_testdir is None:
            self.add_warned("test_dir_exists", "nf-test directory is missing", Path(self.module.component_dir, "tests"))
            return False

        if not self.module.nftest_testdir.is_dir():
            self.add_failed("test_dir_exists", "nf-test directory is missing")
            return False

        self.add_passed("test_dir_exists", "nf-test test directory exists", self.module.nftest_testdir)

        # Validate main.nf.test file
        if self.module.nftest_main_nf is None:
            self.add_warned(
                "test_main_nf_exists",
                "test `main.nf.test` does not exist",
                Path(self.module.component_dir, "tests", "main.nf.test"),
            )
            return False

        if not self.module.nftest_main_nf.is_file():
            self.add_failed("test_main_nf_exists", "test `main.nf.test` does not exist", self.module.nftest_main_nf)
            return False

        self.add_passed("test_main_nf_exists", "test `main.nf.test` exists", self.module.nftest_main_nf)
        return True


class SnapshotFileValidator(ModuleTestValidator):
    """Validates snapshot file existence and JSON parsing."""

    def __init__(self, module: NFCoreComponent):
        super().__init__(module)
        self.snap_file: Optional[Path] = None
        self.snap_content: Optional[dict] = None

    def validate(self) -> bool:
        """Validate snapshot file if needed."""
        if self.module.nftest_main_nf is None or not self.module.nftest_main_nf.is_file():
            return True  # Skip if no main.nf.test file

        # Check if snapshot is needed
        with open(self.module.nftest_main_nf) as fh:
            if "snapshot(" not in fh.read():
                return True  # No snapshot needed

        if self.module.nftest_testdir is None:
            return False  # Cannot proceed without test directory

        self.snap_file = self.module.nftest_testdir / "main.nf.test.snap"

        # Check snapshot file exists
        if not self.snap_file.is_file():
            self.add_failed("test_snapshot_exists", "snapshot file `main.nf.test.snap` does not exist", self.snap_file)
            return False

        self.add_passed("test_snapshot_exists", "snapshot file `main.nf.test.snap` exists", self.snap_file)

        # Parse JSON content
        try:
            with open(self.snap_file) as snap_fh:
                self.snap_content = json.load(snap_fh)
            return True
        except json.decoder.JSONDecodeError as e:
            self.add_failed(
                "test_snapshot_exists", f"snapshot file `main.nf.test.snap` can't be read: {e}", self.snap_file
            )
            return False

    def get_snap_content(self):
        """Get parsed snapshot content."""
        return self.snap_content

    def get_snap_file(self):
        """Get snapshot file path."""
        return self.snap_file


class MD5HashValidator(ModuleTestValidator):
    """Validates against empty file MD5 hashes in snapshots."""

    EMPTY_FILE_MD5 = "d41d8cd98f00b204e9800998ecf8427e"
    COMPRESSED_EMPTY_FILE_MD5 = "7029066c27ac6f5ef18d660d5741979a"

    def __init__(self, module: NFCoreComponent, snap_content: dict, snap_file: Path):
        super().__init__(module)
        self.snap_content = snap_content
        self.snap_file = snap_file

    def validate(self) -> bool:
        """Check for empty file MD5 hashes in snapshot content."""
        if not self.snap_content:
            return True

        for test_name in self.snap_content.keys():
            self._check_empty_file_md5(test_name)
            self._check_compressed_empty_file_md5(test_name)
        return True

    def _check_empty_file_md5(self, test_name: str):
        """Check for empty file MD5 hash."""
        if self.EMPTY_FILE_MD5 in str(self.snap_content[test_name]):
            if "stub" not in test_name:
                self.add_failed(
                    "test_snap_md5sum", f"md5sum for empty file found: {self.EMPTY_FILE_MD5}", self.snap_file
                )
            else:
                self.add_passed(
                    "test_snap_md5sum", "md5sum for empty file found, but it is a stub test", self.snap_file
                )
        else:
            self.add_passed("test_snap_md5sum", "no md5sum for empty file found", self.snap_file)

    def _check_compressed_empty_file_md5(self, test_name: str):
        """Check for compressed empty file MD5 hash."""
        if self.COMPRESSED_EMPTY_FILE_MD5 in str(self.snap_content[test_name]):
            if "stub" not in test_name:
                self.add_failed(
                    "test_snap_md5sum",
                    f"md5sum for compressed empty file found: {self.COMPRESSED_EMPTY_FILE_MD5}",
                    self.snap_file,
                )
            else:
                self.add_passed(
                    "test_snap_md5sum", "md5sum for compressed empty file found, but it is a stub test", self.snap_file
                )
        else:
            self.add_passed("test_snap_md5sum", "no md5sum for compressed empty file found", self.snap_file)


class VersionContentValidator(ModuleTestValidator):
    """Validates version content in snapshots (hash vs actual content)."""

    def __init__(self, module: NFCoreComponent, snap_content: dict, snap_file: Path):
        super().__init__(module)
        self.snap_content = snap_content
        self.snap_file = snap_file

    def validate(self) -> bool:
        """Check version content format for each test."""
        if not self.snap_content:
            return True

        for test_name in self.snap_content.keys():
            if self._has_version_content(test_name):
                self.add_passed("test_snap_versions", "versions found in snapshot file", self.snap_file)
                self._validate_version_content_format(test_name)
            else:
                self.add_failed("test_snap_versions", "versions not found in snapshot file", self.snap_file)
        return True

    def _has_version_content(self, test_name: str) -> bool:
        """Check if test contains version information."""
        return "versions" in str(self.snap_content[test_name]) or "versions" in str(self.snap_content.keys())

    def _validate_version_content_format(self, test_name: str):
        """Validate that version content is actual data, not hash format."""
        if _contains_version_hash(self.snap_content[test_name]):
            # Invalid - contains hash format
            self.add_failed(
                "test_snap_version_content",
                "Version information should contain actual YAML content "
                "(e.g., {'tool': {'version': '1.0'}}), not hash format like 'versions.yml:md5,hash'",
                self.snap_file,
            )
        else:
            # Valid - either contains actual content or no version hash detected
            self.add_passed(
                "test_snap_version_content",
                "version information contains actual content instead of hash",
                self.snap_file,
            )


class TagValidator(ModuleTestValidator):
    """Validates nf-test tags compliance."""

    def validate(self) -> bool:
        """Verify that nf-test tags are correct."""
        if self.module.nftest_main_nf is None or not self.module.nftest_main_nf.is_file():
            return True

        main_nf_tags = self.module._get_main_nf_tags(self.module.nftest_main_nf)
        required_tags = self._get_required_tags()
        chained_components_tags = self.module._get_included_components_in_chained_tests(self.module.nftest_main_nf)

        missing_tags = []
        log.debug(f"Required tags: {required_tags}")
        log.debug(f"Included components for chained nf-tests: {chained_components_tags}")

        for tag in set(required_tags + chained_components_tags):
            if tag not in main_nf_tags:
                missing_tags.append(tag)

        if len(missing_tags) == 0:
            self.add_passed("test_main_tags", "Tags adhere to guidelines", self.module.nftest_main_nf)
        else:
            self.add_failed(
                "test_main_tags",
                f"Tags do not adhere to guidelines. Tags missing in `main.nf.test`: `{','.join(missing_tags)}`",
                self.module.nftest_main_nf,
            )
        return True

    def _get_required_tags(self) -> list:
        """Get list of required tags for this module."""
        not_alphabet = re.compile(r"[^a-zA-Z]")
        org_alp = not_alphabet.sub("", self.module.org)
        org_alphabet = org_alp if org_alp != "" else "nfcore"

        required_tags = ["modules", f"modules_{org_alphabet}", self.module.component_name]
        if self.module.component_name.count("/") == 1:
            required_tags.append(self.module.component_name.split("/")[0])
        return required_tags


class PytestCleanupValidator(ModuleTestValidator):
    """Validates that old pytest files are properly cleaned up."""

    def validate(self) -> bool:
        """Check pytest_modules.yml and old test directory cleanup."""
        self._check_pytest_yml()
        self._check_old_test_directory()
        return True

    def _check_pytest_yml(self):
        """Check pytest_modules.yml does not contain entries for modules with nf-test."""
        pytest_yml_path = self.module.base_dir / "tests" / "config" / "pytest_modules.yml"

        # Determine if this is a pytest module
        repo_dir = self.module.component_dir.parts[
            : self.module.component_dir.parts.index(self.module.component_name.split("/")[0])
        ][-1]
        test_dir = Path(self.module.base_dir, "tests", "modules", repo_dir, self.module.component_name)
        pytest_main_nf = Path(test_dir, "main.nf")
        is_pytest = pytest_main_nf.is_file()

        if pytest_yml_path.is_file() and not is_pytest:
            try:
                with open(pytest_yml_path) as fh:
                    pytest_yml = yaml.safe_load(fh)
                    if self.module.component_name in pytest_yml.keys():
                        self.add_failed(
                            "test_pytest_yml",
                            "module with nf-test should not be listed in pytest_modules.yml",
                            pytest_yml_path,
                        )
                    else:
                        self.add_passed(
                            "test_pytest_yml", "module with  nf-test not in pytest_modules.yml", pytest_yml_path
                        )
            except FileNotFoundError:
                self.add_warned("test_pytest_yml", "Could not open pytest_modules.yml file", pytest_yml_path)

    def _check_old_test_directory(self):
        """Check that old test directory does not exist."""
        # Determine if this is a pytest module
        repo_dir = self.module.component_dir.parts[
            : self.module.component_dir.parts.index(self.module.component_name.split("/")[0])
        ][-1]
        test_dir = Path(self.module.base_dir, "tests", "modules", repo_dir, self.module.component_name)
        pytest_main_nf = Path(test_dir, "main.nf")
        is_pytest = pytest_main_nf.is_file()

        if not is_pytest:
            old_test_dir = Path(self.module.base_dir, "tests", "modules", self.module.component_name)
            if old_test_dir.is_dir():
                self.add_failed(
                    "test_old_test_dir",
                    f"Pytest files are still present at `{Path('tests', 'modules', self.module.component_name)}`. "
                    "Please remove this directory and its contents.",
                    old_test_dir,
                )
            else:
                self.add_passed("test_old_test_dir", "Old pytests don't exist for this module", old_test_dir)


def _contains_version_hash(test_content):
    """
    Check if test content contains version information in hash format.

    Uses precise regex patterns to detect version hash formats while avoiding
    false positives from similar strings.

    Args:
        test_content: Content of a single test from snapshot

    Returns:
        bool: True if hash format detected, False otherwise
    """
    # More precise regex patterns with proper boundaries
    version_hash_patterns = [
        r"\bversions\.yml:md5,[a-f0-9]{32}\b",  # Exact MD5 format (32 hex chars)
        r"\bversions\.yml:sha[0-9]*,[a-f0-9]+\b",  # SHA format with variable length
    ]

    # Convert to string only once and search efficiently
    content_str = str(test_content)

    for pattern in version_hash_patterns:
        if re.search(pattern, content_str):
            return True

    return False


class ModuleTestRunner:
    """Orchestrates all module test validators."""

    def __init__(self, module: NFCoreComponent, allow_missing: bool = False):
        self.module = module
        self.allow_missing = allow_missing

    def run_all_validators(self):
        """Run all validators in the correct order."""
        # Early exit for missing test directory
        if self.module.nftest_testdir is None:
            if self.allow_missing:
                self.module.warned.append(
                    (
                        "test_dir_exists",
                        "nf-test directory is missing",
                        Path(self.module.component_dir, "tests"),
                    )
                )
                return
            raise LintExceptionError("Module does not have a `tests` dir")

        # Early exit for missing main.nf.test
        if self.module.nftest_main_nf is None:
            if self.allow_missing:
                self.module.warned.append(
                    (
                        "test_main_nf_exists",
                        "test `main.nf.test` does not exist",
                        Path(self.module.component_dir, "tests", "main.nf.test"),
                    )
                )
                return
            raise LintExceptionError("Module does not have a `tests` dir")

        # Step 1: Validate directory structure
        directory_validator = TestDirectoryValidator(self.module)
        if not directory_validator.validate():
            return  # Early exit if directory structure is invalid

        # Step 2: Validate snapshot file and parse content
        snapshot_validator = SnapshotFileValidator(self.module)
        if not snapshot_validator.validate():
            return  # Early exit if snapshot validation fails

        snap_content = snapshot_validator.get_snap_content()
        snap_file = snapshot_validator.get_snap_file()

        # Step 3: Run content validators if we have snapshot content
        if snap_content and snap_file:
            # MD5 hash validation
            md5_validator = MD5HashValidator(self.module, snap_content, snap_file)
            md5_validator.validate()

            # Version content validation
            version_validator = VersionContentValidator(self.module, snap_content, snap_file)
            version_validator.validate()

        # Step 4: Validate tags
        tag_validator = TagValidator(self.module)
        tag_validator.validate()

        # Step 5: Validate pytest cleanup
        pytest_validator = PytestCleanupValidator(self.module)
        pytest_validator.validate()


def module_tests(_, module: NFCoreComponent, allow_missing: bool = False):
    """
    Lint the tests of a module in ``nf-core/modules``

    It verifies that the test directory exists
    and contains a ``main.nf.test`` and a ``main.nf.test.snap``

    This function uses a modular validator system for better maintainability
    and readability of the validation logic.
    """
    runner = ModuleTestRunner(module, allow_missing)
    runner.run_all_validators()
