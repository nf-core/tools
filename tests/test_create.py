"""Some tests covering the pipeline creation sub command."""

import os
import unittest
from pathlib import Path
from unittest import mock

import git
import yaml

import nf_core.create

from .utils import with_temporary_folder

TEST_DATA_DIR = Path(__file__).parent / "data"
PIPELINE_TEMPLATE_YML = TEST_DATA_DIR / "pipeline_create_template.yml"
PIPELINE_TEMPLATE_YML_SKIP = TEST_DATA_DIR / "pipeline_create_template_skip.yml"


class NfcoreCreateTest(unittest.TestCase):
    def setUp(self):
        self.pipeline_name = "nf-core/test"
        self.pipeline_description = "just for 4w3s0m3 tests"
        self.pipeline_author = "Chuck Norris"
        self.pipeline_version = "1.0.0"
        self.default_branch = "default"

    def test_pipeline_creation(self):
        pipeline = nf_core.create.PipelineCreate(
            name=self.pipeline_name,
            description=self.pipeline_description,
            author=self.pipeline_author,
            version=self.pipeline_version,
            no_git=False,
            force=True,
            plain=True,
            default_branch=self.default_branch,
        )

        assert pipeline.template_params["name"] == self.pipeline_name
        assert pipeline.template_params["description"] == self.pipeline_description
        assert pipeline.template_params["author"] == self.pipeline_author
        assert pipeline.template_params["version"] == self.pipeline_version

    @with_temporary_folder
    def test_pipeline_creation_initiation(self, tmp_path):
        pipeline = nf_core.create.PipelineCreate(
            name=self.pipeline_name,
            description=self.pipeline_description,
            author=self.pipeline_author,
            version=self.pipeline_version,
            no_git=False,
            force=True,
            outdir=tmp_path,
            plain=True,
            default_branch=self.default_branch,
        )
        pipeline.init_pipeline()
        assert os.path.isdir(os.path.join(pipeline.outdir, ".git"))
        assert f" {self.default_branch}\n" in git.Repo.init(pipeline.outdir).git.branch()
        assert not os.path.exists(os.path.join(pipeline.outdir, "pipeline_template.yml"))
        with open(os.path.join(pipeline.outdir, ".nf-core.yml")) as fh:
            assert "template" not in fh.read()

    @with_temporary_folder
    def test_pipeline_creation_initiation_with_yml(self, tmp_path):
        pipeline = nf_core.create.PipelineCreate(
            name=self.pipeline_name,
            description=self.pipeline_description,
            author=self.pipeline_author,
            version=self.pipeline_version,
            no_git=False,
            force=True,
            outdir=tmp_path,
            template_yaml_path=PIPELINE_TEMPLATE_YML,
            plain=True,
            default_branch=self.default_branch,
        )
        pipeline.init_pipeline()
        assert os.path.isdir(os.path.join(pipeline.outdir, ".git"))
        assert f" {self.default_branch}\n" in git.Repo.init(pipeline.outdir).git.branch()

        # Check pipeline template yml has been dumped to `.nf-core.yml` and matches input
        assert not os.path.exists(os.path.join(pipeline.outdir, "pipeline_template.yml"))
        assert os.path.exists(os.path.join(pipeline.outdir, ".nf-core.yml"))
        with open(os.path.join(pipeline.outdir, ".nf-core.yml")) as fh:
            nfcore_yml = yaml.safe_load(fh)
            assert "template" in nfcore_yml
            assert nfcore_yml["template"] == yaml.safe_load(PIPELINE_TEMPLATE_YML.read_text())

    @mock.patch.object(nf_core.create.PipelineCreate, "customize_template")
    @mock.patch.object(nf_core.create.questionary, "confirm")
    @with_temporary_folder
    def test_pipeline_creation_initiation_customize_template(self, mock_questionary, mock_customize, tmp_path):
        mock_questionary.unsafe_ask.return_value = True
        mock_customize.return_value = {"prefix": "testprefix"}
        pipeline = nf_core.create.PipelineCreate(
            name=self.pipeline_name,
            description=self.pipeline_description,
            author=self.pipeline_author,
            version=self.pipeline_version,
            no_git=False,
            force=True,
            outdir=tmp_path,
            default_branch=self.default_branch,
        )
        pipeline.init_pipeline()
        assert os.path.isdir(os.path.join(pipeline.outdir, ".git"))
        assert f" {self.default_branch}\n" in git.Repo.init(pipeline.outdir).git.branch()

        # Check pipeline template yml has been dumped to `.nf-core.yml` and matches input
        assert not os.path.exists(os.path.join(pipeline.outdir, "pipeline_template.yml"))
        assert os.path.exists(os.path.join(pipeline.outdir, ".nf-core.yml"))
        with open(os.path.join(pipeline.outdir, ".nf-core.yml")) as fh:
            nfcore_yml = yaml.safe_load(fh)
            assert "template" in nfcore_yml
            assert nfcore_yml["template"] == yaml.safe_load(PIPELINE_TEMPLATE_YML.read_text())

    @with_temporary_folder
    def test_pipeline_creation_with_yml_skip(self, tmp_path):
        pipeline = nf_core.create.PipelineCreate(
            name=self.pipeline_name,
            description=self.pipeline_description,
            author=self.pipeline_author,
            version=self.pipeline_version,
            no_git=False,
            force=True,
            outdir=tmp_path,
            template_yaml_path=PIPELINE_TEMPLATE_YML_SKIP,
            plain=True,
            default_branch=self.default_branch,
        )
        pipeline.init_pipeline()
        assert not os.path.isdir(os.path.join(pipeline.outdir, ".git"))

        # Check pipeline template yml has been dumped to `.nf-core.yml` and matches input
        assert not os.path.exists(os.path.join(pipeline.outdir, "pipeline_template.yml"))
        assert os.path.exists(os.path.join(pipeline.outdir, ".nf-core.yml"))
        with open(os.path.join(pipeline.outdir, ".nf-core.yml")) as fh:
            nfcore_yml = yaml.safe_load(fh)
            assert "template" in nfcore_yml
            assert nfcore_yml["template"] == yaml.safe_load(PIPELINE_TEMPLATE_YML_SKIP.read_text())

        # Check that some of the skipped files are not present
        assert not os.path.exists(os.path.join(pipeline.outdir, "CODE_OF_CONDUCT.md"))
        assert not os.path.exists(os.path.join(pipeline.outdir, ".github"))
        assert not os.path.exists(os.path.join(pipeline.outdir, "conf", "igenomes.config"))
