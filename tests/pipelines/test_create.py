"""Some tests covering the pipeline creation sub command."""

import os
import unittest
from pathlib import Path

import git
import jinja2
import yaml

import nf_core.pipelines.create.create
from nf_core.pipelines.create.utils import load_features_yaml

from ..utils import TEST_DATA_DIR, with_temporary_folder

PIPELINE_TEMPLATE_YML = TEST_DATA_DIR / "pipeline_create_template.yml"
PIPELINE_TEMPLATE_YML_SKIP = TEST_DATA_DIR / "pipeline_create_template_skip.yml"


class NfcoreCreateTest(unittest.TestCase):
    def setUp(self):
        self.pipeline_name = "nf-core/test"
        self.pipeline_description = "just for 4w3s0m3 tests"
        self.pipeline_author = "Chuck Norris"
        self.pipeline_version = "1.0.0"
        self.default_branch = "default"

    @with_temporary_folder
    def test_pipeline_creation(self, tmp_path):
        pipeline = nf_core.pipelines.create.create.PipelineCreate(
            name=self.pipeline_name,
            description=self.pipeline_description,
            author=self.pipeline_author,
            version=self.pipeline_version,
            no_git=False,
            force=True,
            outdir=tmp_path,
            default_branch=self.default_branch,
        )

        assert pipeline.config.name == self.pipeline_name
        assert pipeline.config.description == self.pipeline_description
        assert pipeline.config.author == self.pipeline_author
        assert pipeline.config.version == self.pipeline_version

    @with_temporary_folder
    def test_pipeline_creation_initiation(self, tmp_path):
        pipeline = nf_core.pipelines.create.create.PipelineCreate(
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
        assert Path(pipeline.outdir, ".git").is_dir()
        assert f" {self.default_branch}\n" in git.Repo.init(pipeline.outdir).git.branch()
        assert not Path(pipeline.outdir, "pipeline_template.yml").exists()
        with open(Path(pipeline.outdir, ".nf-core.yml")) as fh:
            assert "template" in fh.read()

    @with_temporary_folder
    def test_pipeline_creation_initiation_with_yml(self, tmp_path):
        pipeline = nf_core.pipelines.create.create.PipelineCreate(
            no_git=False,
            outdir=tmp_path,
            template_config=PIPELINE_TEMPLATE_YML,
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
            assert yaml.safe_load(PIPELINE_TEMPLATE_YML.read_text()).items() <= nfcore_yml["template"].items()

    @with_temporary_folder
    def test_pipeline_creation_initiation_customize_template(self, tmp_path):
        pipeline = nf_core.pipelines.create.create.PipelineCreate(
            outdir=tmp_path, template_config=PIPELINE_TEMPLATE_YML, default_branch=self.default_branch
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
            assert yaml.safe_load(PIPELINE_TEMPLATE_YML.read_text()).items() <= nfcore_yml["template"].items()

    @with_temporary_folder
    def test_pipeline_creation_with_yml_skip(self, tmp_path):
        # Update pipeline_create_template_skip.yml file
        template_features_yml = load_features_yaml()
        all_features = list(template_features_yml.keys())
        all_features.remove("is_nfcore")
        env = jinja2.Environment(loader=jinja2.PackageLoader("tests", "data"), keep_trailing_newline=True)
        skip_template = env.get_template(
            str(PIPELINE_TEMPLATE_YML_SKIP.relative_to(Path(nf_core.__file__).parent.parent / "tests" / "data"))
        )
        rendered_content = skip_template.render({"all_features": all_features})
        rendered_yaml = Path(tmp_path) / "pipeline_create_template_skip.yml"
        with open(rendered_yaml, "w") as fh:
            fh.write(rendered_content)

        pipeline = nf_core.pipelines.create.create.PipelineCreate(
            outdir=tmp_path,
            template_config=rendered_yaml,
            default_branch=self.default_branch,
        )
        pipeline.init_pipeline()

        # Check pipeline template yml has been dumped to `.nf-core.yml` and matches input
        assert not (pipeline.outdir / "pipeline_template.yml").exists()
        assert (pipeline.outdir / ".nf-core.yml").exists()
        with open(pipeline.outdir / ".nf-core.yml") as fh:
            nfcore_yml = yaml.safe_load(fh)
            assert "template" in nfcore_yml
            assert yaml.safe_load(PIPELINE_TEMPLATE_YML.read_text()).items() <= nfcore_yml["template"].items()

        # Check that some of the skipped files are not present
        assert not (pipeline.outdir / "CODE_OF_CONDUCT.md").exists()
        assert not (pipeline.outdir / ".github").exists()
        assert not (pipeline.outdir / "conf" / "igenomes.config").exists()
        assert not (pipeline.outdir / ".editorconfig").exists()
