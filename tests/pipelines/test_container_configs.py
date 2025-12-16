"""Tests for the ContainerConfigs helper used by pipelines."""

from unittest.mock import patch

import pytest
import ruamel.yaml

from nf_core.modules.install import ModuleInstall
from nf_core.pipelines.containers_utils import ContainerConfigs
from nf_core.utils import NF_INSPECT_MIN_NF_VERSION, pretty_nf_version

from ..test_pipelines import TestPipelines

yaml = ruamel.yaml.YAML()


class TestContainerConfigs(TestPipelines):
    """Tests for ContainerConfigs using a test pipeline."""

    def setUp(self) -> None:
        super().setUp()
        self.container_configs = ContainerConfigs(self.pipeline_dir, "nf-core")

    def test_check_nextflow_version_sufficient_ok(self) -> None:
        """check_nextflow_version should return silently when version is sufficient."""
        with patch(
            "nf_core.pipelines.containers_utils.check_nextflow_version",
            return_value=True,
        ) as mocked_check:
            self.container_configs.check_nextflow_version_sufficient()

        mocked_check.assert_called_once_with(NF_INSPECT_MIN_NF_VERSION)

    def test_check_nextflow_version_sufficient_too_low(self) -> None:
        """check_nextflow_version should raise UserWarning when version is too low."""
        with patch(
            "nf_core.pipelines.containers_utils.check_nextflow_version",
            return_value=False,
        ):
            with pytest.raises(UserWarning) as excinfo:
                self.container_configs.check_nextflow_version_sufficient()

        # Error message should mention the minimal required version
        assert pretty_nf_version(NF_INSPECT_MIN_NF_VERSION) in str(excinfo.value)

    def test_generate_all_container_configs(self) -> None:
        """Run generate_all_container_configs in a pipeline."""
        # Install fastqc and multiqc from gitlub seqera-containers test branch
        mods_install = ModuleInstall(
            self.pipeline_dir,
            prompt=False,
            force=False,
        )
        mods_install.install("fastqc")
        mods_install.install("multiqc")

        self.container_configs.generate_container_configs()

        conf_dir = self.pipeline_dir / "conf"
        # Expected platforms and one expected container
        platforms: dict[str, list[str]] = {
            "docker_amd64": ["docker", "linux_amd64", "name"],
            "docker_arm64": ["docker", "linux_arm64", "name"],
            "singularity_oras_amd64": ["singularity", "linux_amd64", "name"],
            "singularity_oras_arm64": ["singularity", "linux_arm64", "name"],
            "singularity_https_amd64": ["singularity", "linux_amd64", "https"],
            "singularity_https_arm64": ["singularity", "linux_arm64", "https"],
            "conda_amd64_lockfile": ["conda", "linux_amd64", "lock_file"],
            "conda_arm64_lockfile": ["conda", "linux_arm64", "lock_file"],
        }

        with open(self.pipeline_dir / "modules" / "nf-core" / "fastqc" / "meta.yml") as fh:
            fastqc_meta_yml = yaml.load(fh)

        for p_name, (runtime, arch, protocol) in platforms.items():
            cfg_path = conf_dir / f"containers_{p_name}.config"
            assert cfg_path.exists()
            with cfg_path.open("r") as fh:
                content = fh.readlines()
                value = fastqc_meta_yml["containers"][runtime][arch][protocol]
                assert f"process {{ withName: 'FASTQC' {{ container = '{value}' }} }}\n" in content
