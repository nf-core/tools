"""Some tests covering the bump_version code."""

import logging

import yaml

import nf_core.pipelines.bump_version
import nf_core.utils

from ..test_pipelines import TestPipelines


class TestBumpVersion(TestPipelines):
    def test_bump_pipeline_version(self):
        """Test that making a release with the working example files works"""

        # Bump the version number
        nf_core.pipelines.bump_version.bump_pipeline_version(self.pipeline_obj, "1.1.0")
        new_pipeline_obj = nf_core.utils.Pipeline(self.pipeline_dir)

        # Check nextflow.config
        new_pipeline_obj.load_pipeline_config()
        assert new_pipeline_obj.nf_config["manifest.version"].strip("'\"") == "1.1.0"

        # Check multiqc_config.yml
        with open(new_pipeline_obj._fp("assets/multiqc_config.yml")) as fh:
            multiqc_config = yaml.safe_load(fh)

            assert "report_comment" in multiqc_config
            assert "/releases/tag/1.1.0" in multiqc_config["report_comment"]

        # Check .nf-core.yml
        with open(new_pipeline_obj._fp(".nf-core.yml")) as fh:
            nf_core_yml = yaml.safe_load(fh)
            if nf_core_yml["template"]:
                assert nf_core_yml["template"]["version"] == "1.1.0"

    def test_dev_bump_pipeline_version(self):
        """Test that making a release works with a dev name and a leading v"""
        # Bump the version number
        nf_core.pipelines.bump_version.bump_pipeline_version(self.pipeline_obj, "v1.2dev")
        new_pipeline_obj = nf_core.utils.Pipeline(self.pipeline_dir)

        # Check the pipeline config
        new_pipeline_obj.load_pipeline_config()
        assert new_pipeline_obj.nf_config["manifest.version"].strip("'\"") == "1.2dev"

    def test_bump_nextflow_version(self):
        # Bump the version number to a specific version, preferably one
        # we're not already on
        version = "25.04.2"
        nf_core.pipelines.bump_version.bump_nextflow_version(self.pipeline_obj, version)
        new_pipeline_obj = nf_core.utils.Pipeline(self.pipeline_dir)
        new_pipeline_obj._load()

        # Check nextflow.config
        assert new_pipeline_obj.nf_config["manifest.nextflowVersion"].strip("'\"") == f"!>={version}"

        # Check .github/workflows/nf-test.yml
        with open(new_pipeline_obj._fp(".github/workflows/nf-test.yml")) as fh:
            ci_yaml = yaml.safe_load(fh)
        assert ci_yaml["jobs"]["nf-test"]["strategy"]["matrix"]["NXF_VER"][0] == version

        # Check README.md
        with open(new_pipeline_obj._fp("README.md")) as fh:
            readme = fh.read().splitlines()
        assert (
            f"[![Nextflow](https://img.shields.io/badge/version-%E2%89%A5{version}-green?style=flat&logo=nextflow&logoColor=white&color=%230DC09D&link=https%3A%2F%2Fnextflow.io)]"
            "(https://www.nextflow.io/)" in readme
        )

    def test_bump_pipeline_version_in_snapshot(self):
        """Test that bump version also updates versions in the snapshot."""

        # Create dummy snapshot
        snapshot_dir = self.pipeline_dir / "tests" / "pipeline"

        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_fn = snapshot_dir / "main.nf.test.snap"
        snapshot_fn.touch()
        # write version number in snapshot
        with open(snapshot_fn, "w") as fh:
            fh.write("nf-core/testpipeline=1.0.0dev")

        # Bump the version number
        nf_core.pipelines.bump_version.bump_pipeline_version(self.pipeline_obj, "1.1.0")

        # Check the snapshot
        with open(snapshot_fn) as fh:
            assert fh.read().strip() == "nf-core/testpipeline=1.1.0"

    def test_bump_pipeline_version_in_snapshot_no_version(self):
        """Test that bump version does not update versions in the snapshot if no version is given."""

        # Create dummy snapshot
        snapshot_dir = self.pipeline_dir / "tests" / "pipeline"

        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_fn = snapshot_dir / "main2.nf.test.snap"
        snapshot_fn.touch()
        with open(snapshot_fn, "w") as fh:
            fh.write("test")
        # assert log info message
        self.caplog.set_level(logging.INFO)
        nf_core.pipelines.bump_version.bump_pipeline_version(self.pipeline_obj, "1.1.0")
        assert "Could not find version number in " in self.caplog.text
