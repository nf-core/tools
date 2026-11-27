"""Tests for the ContainerConfigs helper used by pipelines."""

import shutil

import pytest
import ruamel.yaml

from nf_core.commands_pipelines import pipelines_containers_create_configs
from nf_core.modules.install import ModuleInstall
from nf_core.pipelines.containers_utils import PLATFORMS, ContainerConfigs

from ..test_pipelines import TestPipelines

yaml = ruamel.yaml.YAML()


class TestContainerConfigs(TestPipelines):
    """Tests for ContainerConfigs using a test pipeline."""

    def setUp(self) -> None:
        super().setUp()
        self.container_configs = ContainerConfigs(self.pipeline_dir)

    def test_generate_all_container_configs(self) -> None:
        """Run generate_all_container_configs in a pipeline."""
        # Install fastqc and multiqc
        mods_install = ModuleInstall(
            self.pipeline_dir, prompt=False, force=False, sha="79b36b51048048374b642289bfe9e591ef56fe05"
        )
        mods_install.install("fastqc")
        mods_install.install("multiqc")

        self.container_configs.generate_container_configs()

        conf_dir = self.pipeline_dir / "conf"
        with open(self.pipeline_dir / "modules" / "nf-core" / "fastqc" / "meta.yml") as fh:
            fastqc_meta_yml = yaml.load(fh)

        for p_name, (runtime, arch, protocol) in PLATFORMS.items():
            cfg_path = conf_dir / f"containers_{p_name}.config"
            if runtime == "conda":
                # The pinned modules ship pixi lock files, which conda cannot read
                assert not cfg_path.exists() or "FASTQC" not in cfg_path.read_text()
                continue
            assert cfg_path.exists()
            with cfg_path.open("r") as fh:
                content = fh.readlines()
                value = fastqc_meta_yml["containers"][runtime][arch][protocol]
                assert f"process {{ withName: 'FASTQC' {{ container = '{value}' }} }}\n" in content

    def test_generate_container_configs_newly_installed_module(self) -> None:
        """A newly installed module is picked up from disk by the filesystem scan."""
        mods_install = ModuleInstall(
            self.pipeline_dir, prompt=False, force=False, sha="79b36b51048048374b642289bfe9e591ef56fe05"
        )
        mods_install.install("fastqc")

        with open(self.pipeline_dir / "modules" / "nf-core" / "fastqc" / "meta.yml") as fh:
            fastqc_meta_yml = yaml.load(fh)

        self.container_configs.generate_container_configs()

        conf_dir = self.pipeline_dir / "conf"
        for p_name, (runtime, arch, protocol) in PLATFORMS.items():
            cfg_path = conf_dir / f"containers_{p_name}.config"
            if runtime == "conda":
                # The pinned modules ship pixi lock files, which conda cannot read
                assert not cfg_path.exists() or "FASTQC" not in cfg_path.read_text()
                continue
            assert cfg_path.exists()
            value = fastqc_meta_yml["containers"][runtime][arch][protocol]
            assert f"process {{ withName: 'FASTQC' {{ container = '{value}' }} }}\n" in cfg_path.read_text()

    def _write_local_module_with_lock(self, lock_text: str) -> str:
        """Create a local module whose meta.yml points at a conda lock file with *lock_text*."""
        module_dir = self.pipeline_dir / "modules" / "local" / "locked"
        (module_dir / ".conda-lock").mkdir(parents=True, exist_ok=True)
        lock_rel = "modules/local/locked/.conda-lock/linux_amd64-bd-abc_1.txt"
        (self.pipeline_dir / lock_rel).write_text(lock_text)
        (module_dir / "meta.yml").write_text(
            "name: locked\n"
            "containers:\n"
            "  docker:\n"
            "    linux/amd64:\n"
            "      name: community.wave.seqera.io/library/tool:1.0--abc\n"
            "  conda:\n"
            "    linux/amd64:\n"
            f"      lock_file: {lock_rel}\n"
        )
        (module_dir / "main.nf").write_text('process LOCKED {\n  script:\n  """\n  echo hello\n  """\n}\n')
        return lock_rel

    def test_generate_container_configs_keeps_explicit_conda_lock(self) -> None:
        """Conda @EXPLICIT lock files are written to the conda lock config."""
        lock_rel = self._write_local_module_with_lock(
            "@EXPLICIT\nhttps://conda.anaconda.org/bioconda/linux-64/tool-1.0-0.conda#abc\n"
        )
        self.container_configs.generate_container_configs()
        cfg = self.pipeline_dir / "conf" / "containers_conda_lock_files_amd64.config"
        assert f"process {{ withName: 'LOCKED' {{ conda = '{lock_rel}' }} }}\n" in cfg.read_text()

    def test_generate_container_configs_skips_pixi_conda_lock(self) -> None:
        """Pixi lock files cannot be read by conda, so they are left out of the conda lock config."""
        self._write_local_module_with_lock("version: 6\nenvironments: {}\npackages: []\n")
        self.container_configs.generate_container_configs()
        cfg = self.pipeline_dir / "conf" / "containers_conda_lock_files_amd64.config"
        assert not cfg.exists() or "LOCKED" not in cfg.read_text()
        docker_cfg = self.pipeline_dir / "conf" / "containers_docker_amd64.config"
        assert "LOCKED" in docker_cfg.read_text()

    def test_generate_container_configs_removes_stale_entries(self) -> None:
        """Stale entries are not present after regeneration."""
        conf_dir = self.pipeline_dir / "conf"
        stale_line = "process { withName: 'REMOVED_MODULE' { container = 'stale/image:latest' } }\n"
        for p_name in PLATFORMS:
            (conf_dir / f"containers_{p_name}.config").write_text(stale_line)

        self.container_configs.generate_container_configs()

        for p_name in PLATFORMS:
            cfg_path = conf_dir / f"containers_{p_name}.config"
            if cfg_path.exists():
                assert stale_line not in cfg_path.read_text(), (
                    f"{cfg_path.name} still contains stale entry after regeneration"
                )

    def test_generate_container_configs_no_modules_dir(self) -> None:
        """Returns an empty set immediately when there is no modules/ directory."""
        shutil.rmtree(self.pipeline_dir / "modules", ignore_errors=True)
        result = self.container_configs.generate_container_configs()
        assert result == set()

    def test_generate_container_configs_skips_meta_without_containers(self) -> None:
        """meta.yml files without a containers key are silently ignored."""
        module_dir = self.pipeline_dir / "modules" / "local" / "fake"
        module_dir.mkdir(parents=True, exist_ok=True)
        (module_dir / "meta.yml").write_text("name: fake\ndescription: no containers here\n")
        (module_dir / "main.nf").write_text('process FAKE {\n  script:\n  """\n  echo hello\n  """\n}\n')

        self.container_configs.generate_container_configs()

        conf_dir = self.pipeline_dir / "conf"
        for p_name in PLATFORMS:
            cfg_path = conf_dir / f"containers_{p_name}.config"
            if cfg_path.exists():
                assert "FAKE" not in cfg_path.read_text(), f"{cfg_path.name} contains entry for FAKE module"


class TestPipelinesContainersCommand(TestPipelines):
    """Tests for the ``nf-core pipelines containers`` command function."""

    def test_regenerates_config_files(self) -> None:
        """Existing config file contents are replaced."""
        cfg_path = self.pipeline_dir / "conf" / "containers_docker_amd64.config"
        original = cfg_path.read_text()
        cfg_path.write_text("not a container config\n")

        pipelines_containers_create_configs(None, str(self.pipeline_dir))

        assert cfg_path.read_text() == original

    def test_exits_when_not_a_pipeline(self) -> None:
        """A directory without main.nf exits with an error."""
        with pytest.raises(SystemExit):
            pipelines_containers_create_configs(None, str(self.tmp_dir))
