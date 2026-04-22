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
        self._commit_container_cfg("containers_docker_amd64.config", content)

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
        self._commit_container_cfg("containers_docker_amd64.config", old)

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
        """Linting fails when generate produces a config that has never been committed to the repo."""
        content = "process { withName: 'FASTQC' { container = 'docker.io/biocontainers/fastqc:0.12.1' } }\n"

        repo = git.Repo(self.new_pipeline)
        repo.index.remove(["conf/containers_docker_amd64.config"], working_tree=True)
        repo.index.commit("remove container config to simulate missing file")

        def generate(cc_self):
            (cc_self.workflow_directory / "conf" / "containers_docker_amd64.config").write_text(content)
            return {"containers_docker_amd64.config"}

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
        cfg = self._commit_container_cfg("containers_docker_amd64.config", old)

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
