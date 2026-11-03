from pathlib import Path
from unittest.mock import patch

import nf_core.pipelines.lint
from nf_core.utils import set_wd

from ..test_lint import TestLint

GENERATE = "nf_core.pipelines.containers_utils.ContainerConfigs.generate_container_configs"
OLD = "process { withName: 'FASTQC' { container = 'old_image' } }\n"
NEW = "process { withName: 'FASTQC' { container = 'new_image' } }\n"


class TestLintContainerConfigs(TestLint):
    def setUp(self) -> None:
        super().setUp()
        self.new_pipeline = self._make_pipeline_copy()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _lint(self, writes: dict[str, str | None], fix: tuple[str, ...] = (), wf_path: str | None = None):
        """Run the lint with generation mocked to write (or, for ``None``, delete) the given ``conf/`` files."""

        def generate(cc_self):
            for name, content in writes.items():
                path = cc_self.workflow_directory / "conf" / name
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
            return {name for name, content in writes.items() if content is not None}

        with patch(GENERATE, autospec=True, side_effect=generate):
            lint_obj = nf_core.pipelines.lint.PipelineLint(wf_path or self.new_pipeline, fix=fix)
            lint_obj._load()
            return lint_obj.container_configs()

    def _write_container_cfg(self, name: str, content: str) -> Path:
        path = Path(self.new_pipeline) / "conf" / name
        path.write_text(content)
        return path

    # ------------------------------------------------------------------
    # tests
    # ------------------------------------------------------------------

    def test_container_configs_up_to_date(self):
        """Linting passes when generated configs match what is on disk, committed or not."""
        self._write_container_cfg("containers_docker_amd64.config", NEW)

        result = self._lint({"containers_docker_amd64.config": NEW})

        assert len(result["failed"]) == 0
        assert any("up to date" in p for p in result["passed"])

    def test_container_configs_out_of_date(self):
        """Linting fails when generated configs differ from what is on disk."""
        self._write_container_cfg("containers_docker_amd64.config", OLD)

        result = self._lint({"containers_docker_amd64.config": NEW})

        assert any("out of date" in f for f in result["failed"])

    def test_container_configs_missing_file(self):
        """Linting fails when generate produces a config that did not exist on disk before."""
        (Path(self.new_pipeline) / "conf" / "containers_new_platform.config").unlink(missing_ok=True)

        result = self._lint({"containers_new_platform.config": NEW})

        assert any("missing" in f for f in result["failed"])

    def test_container_configs_fix_overwrites_files(self):
        """--fix overwrites out-of-date container config files and reports them as fixed."""
        cfg = self._write_container_cfg("containers_docker_amd64.config", OLD)

        result = self._lint({"containers_docker_amd64.config": NEW}, fix=("container_configs",))

        assert len(result["failed"]) == 0
        assert any("overwritten" in f for f in result["fixed"])
        assert cfg.read_text() == NEW

    def test_container_configs_user_warning_warns(self):
        """A UserWarning from ContainerConfigs (e.g. low NF version) produces a lint warning."""
        with patch(GENERATE, autospec=True, side_effect=UserWarning("Nextflow version too low")):
            lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
            lint_obj._load()
            result = lint_obj.container_configs()

        assert len(result["failed"]) == 0
        assert any("Nextflow version too low" in w for w in result["warned"])

    def test_container_configs_working_tree_restored_after_lint(self):
        """After lint (without --fix), modified files are restored and newly created files are removed."""
        cfg_path = self._write_container_cfg("containers_docker_amd64.config", OLD)
        new_path = Path(self.new_pipeline) / "conf" / "containers_new_platform.config"
        new_path.unlink(missing_ok=True)

        result = self._lint({"containers_docker_amd64.config": NEW, "containers_new_platform.config": "new platform\n"})

        assert len(result["failed"]) > 0
        assert cfg_path.read_text() == OLD, "Modified file should be restored to original content"
        assert not new_path.exists(), "Newly created file should be removed after lint"

    def test_container_configs_restore_with_relative_wf_path(self):
        """The working tree is restored when the pipeline is linted via a relative path."""
        cfg_path = self._write_container_cfg("containers_docker_amd64.config", OLD)

        with set_wd(Path(self.new_pipeline).parent):
            result = self._lint({"containers_docker_amd64.config": NEW}, wf_path=Path(self.new_pipeline).name)

        assert any("out of date" in f for f in result["failed"])
        assert cfg_path.read_text() == OLD, "Modified file should be restored even when using relative wf_path"

    def test_container_configs_removed_file_restored_after_lint(self):
        """A config deleted by generation (no module provides it anymore) fails lint and is restored."""
        cfg_path = self._write_container_cfg("containers_docker_arm64.config", OLD)

        result = self._lint({"containers_docker_arm64.config": None})

        assert any("obsolete" in f for f in result["failed"])
        assert result["could_fix"]
        assert cfg_path.read_text() == OLD, "Removed file should be restored after lint"

    def test_container_configs_fix_removes_obsolete_file(self):
        """--fix keeps obsolete config files deleted and reports them as fixed."""
        cfg_path = self._write_container_cfg("containers_docker_arm64.config", OLD)

        result = self._lint({"containers_docker_arm64.config": None}, fix=("container_configs",))

        assert len(result["failed"]) == 0
        assert any("removed" in f for f in result["fixed"])
        assert not cfg_path.exists()
