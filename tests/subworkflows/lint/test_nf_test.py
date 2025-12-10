import json
import shutil
from pathlib import Path

import nf_core.subworkflows

from ...test_subworkflows import TestSubworkflows


class TestSubworkflowsNfTest(TestSubworkflows):
    """Test subworkflow nf-test and snapshot functionality"""

    def setUp(self):
        super().setUp()
        self.snap_file = Path(
            self.nfcore_modules,
            "subworkflows",
            "nf-core",
            "test_subworkflow",
            "tests",
            "main.nf.test.snap",
        )

    def test_subworkflows_lint_snapshot_file(self):
        """Test linting a subworkflow with a snapshot file"""
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_lint_snapshot_file_missing_fail(self):
        """Test linting a subworkflow with a snapshot file missing, which should fail"""
        self.snap_file.unlink()
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        self.snap_file.touch()
        assert len(subworkflow_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_lint_snapshot_file_not_needed(self):
        """Test linting a subworkflow which doesn't need a snapshot file by removing the snapshot keyword in the main.nf.test file"""
        with open(
            Path(
                self.nfcore_modules,
                "subworkflows",
                "nf-core",
                "test_subworkflow",
                "tests",
                "main.nf.test",
            )
        ) as fh:
            content = fh.read()
            new_content = content.replace("snapshot(", "snap (")
        with open(
            Path(
                self.nfcore_modules,
                "subworkflows",
                "nf-core",
                "test_subworkflow",
                "tests",
                "main.nf.test",
            ),
            "w",
        ) as fh:
            fh.write(new_content)

        self.snap_file.unlink()
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        Path(
            self.nfcore_modules,
            "subworkflows",
            "nf-core",
            "test_subworkflow",
            "tests",
            "main.nf.test.snap",
        ).touch()
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_absent_version(self):
        """Test linting a nf-test subworkflow if the versions is absent in the snapshot file `"""

        with open(self.snap_file) as fh:
            content = fh.read()
            new_content = content.replace("versions", "foo")
        with open(self.snap_file, "w") as fh:
            fh.write(new_content)

        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        assert len(subworkflow_lint.failed) == 0
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0, f"Linting warned with {[x.__dict__ for x in subworkflow_lint.warned]}"
        assert any([x.lint_test == "test_snap_versions" for x in subworkflow_lint.warned])

    def test_subworkflows_empty_file_in_snapshot(self):
        """Test linting a nf-test subworkflow with an empty file sha sum in the test snapshot, which should make it fail (if it is not a stub)"""

        snap = json.load(self.snap_file.open())
        snap["my test"]["content"][0]["0"] = "test:md5,d41d8cd98f00b204e9800998ecf8427e"

        with open(self.snap_file, "w") as fh:
            json.dump(snap, fh)

        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        assert len(subworkflow_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
        assert subworkflow_lint.failed[0].lint_test == "test_snap_md5sum"

    def test_subworkflows_empty_file_in_stub_snapshot(self):
        """Test linting a nf-test subworkflow with an empty file sha sum in the stub test snapshot, which should make it not fail"""

        content = json.load(self.snap_file.open())
        content["my_test_stub"] = {"content": [{"0": "test:md5,d41d8cd98f00b204e9800998ecf8427e", "versions": {}}]}

        with open(self.snap_file, "w") as fh:
            json.dump(content, fh)

        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
        assert any(x.lint_test == "test_snap_md5sum" for x in subworkflow_lint.passed)

    def test_subworkflows_missing_test_dir(self):
        """Test linting a nf-test subworkflow if the tests directory is missing"""
        test_dir = self.snap_file.parent
        shutil.rmtree(test_dir)

        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(self.nfcore_modules)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        assert len(subworkflow_lint.failed) == 1
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0, f"Linting warned with {[x.__dict__ for x in subworkflow_lint.warned]}"
        assert any([x.lint_test == "test_dir_exists" for x in subworkflow_lint.failed])
