from pathlib import Path
from unittest.mock import patch

import git

import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintContainerConfigs(TestLint):
    def setUp(self) -> None:
        super().setUp()
        self.new_pipeline = self._make_pipeline_copy()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _lint(self):
        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()
        return lint_obj.container_configs()

    def _write_container_cfg(self, name: str, content: str) -> Path:
        path = Path(self.new_pipeline) / "conf" / name
        path.write_text(content)
        return path

    def _commit_container_cfg(self, name: str, content: str) -> Path:
        """Write and git-commit a container config so it shows up in ``git ls-files``."""
        path = self._write_container_cfg(name, content)
        repo = git.Repo(self.new_pipeline)
        repo.index.add([str(path)])
        repo.index.commit(f"Add {name} for testing")
        return path

    # ------------------------------------------------------------------
    # tests
    # ------------------------------------------------------------------

    def test_container_configs_up_to_date(self):
        """Linting passes when generated configs match what is on disk."""
        content = "process { withName: 'FASTQC' { container = 'docker.io/biocontainers/fastqc:0.12.1' } }\n"
        self._write_container_cfg("containers_docker_amd64.config", content)

        def generate(cc_self):
            (cc_self.workflow_directory / "conf" / "containers_docker_amd64.config").write_text(content)
            return {"containers_docker_amd64.config"}

        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=generate,
        ):
            result = self._lint()

        assert len(result["failed"]) == 0
        assert any("up to date" in p for p in result["passed"])

    def test_container_configs_out_of_date(self):
        """Linting fails when generated configs differ from what is on disk."""
        old = "process { withName: 'FASTQC' { container = 'old_image' } }\n"
        new = "process { withName: 'FASTQC' { container = 'new_image' } }\n"
        self._write_container_cfg("containers_docker_amd64.config", old)

        def generate(cc_self):
            (cc_self.workflow_directory / "conf" / "containers_docker_amd64.config").write_text(new)
            return {"containers_docker_amd64.config"}

        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=generate,
        ):
            result = self._lint()

        assert any("out of date" in f for f in result["failed"])

    def test_container_configs_missing_file(self):
        """Linting fails when generate produces a config that did not exist on disk before."""
        content = "process { withName: 'FASTQC' { container = 'docker.io/biocontainers/fastqc:0.12.1' } }\n"

        # Ensure the file doesn't exist before generation
        target = Path(self.new_pipeline) / "conf" / "containers_new_platform.config"
        target.unlink(missing_ok=True)

        def generate(cc_self):
            (cc_self.workflow_directory / "conf" / "containers_new_platform.config").write_text(content)
            return {"containers_new_platform.config"}

        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=generate,
        ):
            result = self._lint()

        assert any("missing" in f for f in result["failed"])

    def test_container_configs_fix_overwrites_files(self):
        """--fix overwrites out-of-date container config files and reports them as fixed."""
        old = "process { withName: 'FASTQC' { container = 'old_image' } }\n"
        new = "process { withName: 'FASTQC' { container = 'new_image' } }\n"
        cfg = self._write_container_cfg("containers_docker_amd64.config", old)

        def generate(cc_self):
            (cc_self.workflow_directory / "conf" / "containers_docker_amd64.config").write_text(new)
            return {"containers_docker_amd64.config"}

        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=generate,
        ):
            lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline, fix=("container_configs",))
            lint_obj._load()
            result = lint_obj.container_configs()

        assert len(result["failed"]) == 0
        assert any("overwritten" in f for f in result["fixed"])
        assert cfg.read_text() == new

    def test_container_configs_user_warning_warns(self):
        """A UserWarning from ContainerConfigs (e.g. low NF version) produces a lint warning."""
        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=UserWarning("Nextflow version too low"),
        ):
            result = self._lint()

        assert len(result["failed"]) == 0
        assert any("Nextflow version too low" in w for w in result["warned"])

    def test_container_configs_uncommitted_but_correct_passes(self):
        """Lint passes when configs were already regenerated (e.g. by modules update) but not committed.

        This is the key scenario that broke with the old git-diff approach: if modules update
        regenerated configs without committing, repo.index.diff(None) would show them as
        modified vs HEAD, causing false 'out of date' failures. The content-comparison approach
        correctly identifies these as up-to-date since the on-disk content matches what generation
        would produce.
        """
        content = "process { withName: 'FASTQC' { container = 'docker.io/biocontainers/fastqc:0.12.1' } }\n"
        # Write the file but do NOT commit it — simulates modules update having regenerated it
        self._write_container_cfg("containers_docker_amd64.config", content)

        def generate(cc_self):
            # Generation writes the exact same content
            (cc_self.workflow_directory / "conf" / "containers_docker_amd64.config").write_text(content)
            return {"containers_docker_amd64.config"}

        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=generate,
        ):
            result = self._lint()

        assert len(result["failed"]) == 0
        assert any("up to date" in p for p in result["passed"])

    def test_container_configs_working_tree_restored_after_lint(self):
        """After lint (without --fix), the working tree is restored to its pre-lint state.

        This verifies the cleanup/restore logic works correctly: modified files are written
        back to their original content, and newly created files are removed.
        """
        old = "process { withName: 'FASTQC' { container = 'old_image' } }\n"
        new = "process { withName: 'FASTQC' { container = 'new_image' } }\n"
        cfg_path = self._write_container_cfg("containers_docker_amd64.config", old)

        # Also ensure a file that will be "new" doesn't exist
        new_path = Path(self.new_pipeline) / "conf" / "containers_new_platform.config"
        new_path.unlink(missing_ok=True)

        def generate(cc_self):
            # Modify existing file
            (cc_self.workflow_directory / "conf" / "containers_docker_amd64.config").write_text(new)
            # Create a new file
            (cc_self.workflow_directory / "conf" / "containers_new_platform.config").write_text("new platform\n")
            return {"containers_docker_amd64.config", "containers_new_platform.config"}

        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=generate,
        ):
            result = self._lint()

        # Lint should detect issues
        assert len(result["failed"]) > 0

        # But the working tree must be restored
        assert cfg_path.read_text() == old, "Modified file should be restored to original content"
        assert not new_path.exists(), "Newly created file should be removed after lint"

    def test_container_configs_restore_with_relative_wf_path(self):
        """Verify working tree restore works correctly when wf_path is relative.

        This tests the fix for the relative path bug: the old implementation called
        git restore with paths relative to wf_path, which would fail when wf_path
        wasn't the repo root. The new implementation directly writes back snapshotted
        content, so it works regardless of whether wf_path is absolute or relative.
        """
        import os

        old = "process { withName: 'FASTQC' { container = 'old_image' } }\n"
        new = "process { withName: 'FASTQC' { container = 'new_image' } }\n"
        cfg_path = self._write_container_cfg("containers_docker_amd64.config", old)

        def generate(cc_self):
            (cc_self.workflow_directory / "conf" / "containers_docker_amd64.config").write_text(new)
            return {"containers_docker_amd64.config"}

        with patch(
            "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs",
            autospec=True,
            side_effect=generate,
        ):
            # Save original cwd and change to parent directory
            original_cwd = Path.cwd()
            try:
                os.chdir(Path(self.new_pipeline).parent)
                # Use relative path (just the basename) instead of absolute path
                relative_pipeline_path = Path(self.new_pipeline).name
                lint_obj = nf_core.pipelines.lint.PipelineLint(str(relative_pipeline_path))
                lint_obj._load()
                result = lint_obj.container_configs()
            finally:
                os.chdir(original_cwd)

        # Lint should detect the modification as "out of date"
        assert any("out of date" in f for f in result["failed"])

        # But the working tree must still be restored correctly even with relative path
        assert cfg_path.read_text() == old, "Modified file should be restored even when using relative wf_path"
