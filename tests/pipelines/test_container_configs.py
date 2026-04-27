"""Tests for the ContainerConfigs helper used by pipelines."""

from pathlib import Path
from unittest.mock import patch

import pytest
import ruamel.yaml

from nf_core.modules.install import ModuleInstall
from nf_core.pipelines.containers_utils import PLATFORMS, ContainerConfigs
from nf_core.utils import NF_INSPECT_MIN_NF_VERSION, pretty_nf_version

from ..test_pipelines import TestPipelines

yaml = ruamel.yaml.YAML()


class TestContainerConfigs(TestPipelines):
    """Tests for ContainerConfigs using a test pipeline."""

    def setUp(self) -> None:
        super().setUp()
        self.container_configs = ContainerConfigs(self.pipeline_dir)

    def test_check_nextflow_version_sufficient_ok(self) -> None:
        """check_nextflow_version should return silently when version is sufficient."""
        with patch(
            "nf_core.pipelines.containers_utils.check_nextflow_version",
            return_value=True,
        ) as mocked_check:
            self.container_configs.check_nextflow_version_sufficient()

        mocked_check.assert_called_once_with(NF_INSPECT_MIN_NF_VERSION, silent=True)

    def test_check_nextflow_version_sufficient_too_low(self) -> None:
        """check_nextflow_version should raise UserWarning when version is too low."""
        with (
            patch(
                "nf_core.pipelines.containers_utils.check_nextflow_version",
                return_value=False,
            ),
            pytest.raises(UserWarning) as excinfo,
        ):
            self.container_configs.check_nextflow_version_sufficient()

        # Error message should mention the minimal required version
        assert pretty_nf_version(NF_INSPECT_MIN_NF_VERSION) in str(excinfo.value)

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
                assert f"process {{ withName: 'FASTQC' {{ container = '{value}' }} }}\n" in content

    def test_generate_container_configs_new_module_injected(self) -> None:
        """new_module_name/path are used when nextflow inspect doesn't yet know about the module."""
        mods_install = ModuleInstall(
            self.pipeline_dir, prompt=False, force=False, sha="79b36b51048048374b642289bfe9e591ef56fe05"
        )
        mods_install.install("fastqc")

        with open(self.pipeline_dir / "modules" / "nf-core" / "fastqc" / "meta.yml") as fh:
            fastqc_meta_yml = yaml.load(fh)

        with (
            patch("nf_core.pipelines.containers_utils.check_nextflow_version", return_value=True),
            patch(
                "nf_core.pipelines.containers_utils.run_cmd",
                return_value=('{"processes": []}', ""),
            ),
        ):
            self.container_configs.generate_container_configs(
                new_module_path=Path("modules/nf-core/fastqc"),
                new_module_name="fastqc",
            )

        conf_dir = self.pipeline_dir / "conf"
        for p_name, (runtime, arch, protocol) in PLATFORMS.items():
            cfg_path = conf_dir / f"containers_{p_name}.config"
            assert cfg_path.exists()
            value = fastqc_meta_yml["containers"][runtime][arch][protocol]
            assert f"process {{ withName: 'FASTQC' {{ container = '{value}' }} }}\n" in cfg_path.read_text()

    def test_generate_container_configs_removes_stale_entries(self) -> None:
        """Stale config files are deleted when all their modules have been removed."""
        conf_dir = self.pipeline_dir / "conf"
        stale_line = "process { withName: 'REMOVED_MODULE' { container = 'stale/image:latest' } }\n"
        for p_name in PLATFORMS:
            (conf_dir / f"containers_{p_name}.config").write_text(stale_line)

        with (
            patch("nf_core.pipelines.containers_utils.check_nextflow_version", return_value=True),
            patch(
                "nf_core.pipelines.containers_utils.run_cmd",
                return_value=('{"processes": []}', ""),
            ),
        ):
            self.container_configs.generate_container_configs()

        for p_name in PLATFORMS:
            cfg_path = conf_dir / f"containers_{p_name}.config"
            assert not cfg_path.exists(), f"{cfg_path.name} should be deleted when all modules are removed"
