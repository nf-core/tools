"""Tests for the ContainerConfigs helper used by pipelines."""

from pathlib import Path

import ruamel.yaml

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
            assert cfg_path.exists()
            with cfg_path.open("r") as fh:
                content = fh.readlines()
                value = fastqc_meta_yml["containers"][runtime][arch][protocol]
                key = "conda" if p_name.startswith("conda_lock_") else "container"
                assert f"process {{ withName: 'FASTQC' {{ {key} = '{value}' }} }}\n" in content

    def test_generate_container_configs_newly_installed_module(self) -> None:
        """A newly installed module is picked up from disk by the filesystem scan."""
        mods_install = ModuleInstall(
            self.pipeline_dir, prompt=False, force=False, sha="79b36b51048048374b642289bfe9e591ef56fe05"
        )
        mods_install.install("fastqc")

        with open(self.pipeline_dir / "modules" / "nf-core" / "fastqc" / "meta.yml") as fh:
            fastqc_meta_yml = yaml.load(fh)

        # new_module_path/name are kept for backward compat but the scan finds the module regardless
        self.container_configs.generate_container_configs(
            new_module_path=Path("modules/nf-core/fastqc"),
            new_module_name="fastqc",
        )

        conf_dir = self.pipeline_dir / "conf"
        for p_name, (runtime, arch, protocol) in PLATFORMS.items():
            cfg_path = conf_dir / f"containers_{p_name}.config"
            assert cfg_path.exists()
            value = fastqc_meta_yml["containers"][runtime][arch][protocol]
            key = "conda" if p_name.startswith("conda_lock_") else "container"
            assert f"process {{ withName: 'FASTQC' {{ {key} = '{value}' }} }}\n" in cfg_path.read_text()

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
