import json
import os
import shutil
import tempfile
from pathlib import Path

import nf_core.pipelines.create.create
import nf_core.pipelines.schema
from nf_core.pipelines.params_file import ParamsFileBuilder


class TestParamsFileBuilder:
    """Class for schema tests"""

    @classmethod
    def setup_class(cls):
        """Create a new PipelineSchema object"""
        cls.schema_obj = nf_core.pipelines.schema.PipelineSchema()
        cls.root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        # Create a test pipeline in temp directory
        cls.tmp_dir = tempfile.mkdtemp()
        cls.template_dir = Path(cls.tmp_dir, "wf")
        create_obj = nf_core.pipelines.create.create.PipelineCreate(
            "testpipeline", "a description", "Me", outdir=cls.template_dir, no_git=True
        )
        create_obj.init_pipeline()

        cls.template_schema = Path(cls.template_dir, "nextflow_schema.json")
        cls.params_template_builder = ParamsFileBuilder(cls.template_dir)
        cls.invalid_template_schema = Path(cls.template_dir, "nextflow_schema_invalid.json")

        # Remove the allOf section to make the schema invalid
        with open(cls.template_schema) as fh:
            o = json.load(fh)
            del o["allOf"]

        with open(cls.invalid_template_schema, "w") as fh:
            json.dump(o, fh)

    @classmethod
    def teardown_class(cls):
        if Path(cls.tmp_dir).exists():
            shutil.rmtree(cls.tmp_dir)

    def test_build_template(self):
        outfile = Path(self.tmp_dir, "params-file.yml")
        self.params_template_builder.write_params_file(str(outfile))

        assert outfile.exists()

        with open(outfile) as fh:
            out = fh.read()

        assert "nf-core/testpipeline" in out

    def test_build_template_invalid_schema(self, caplog):
        """Build a schema from a template"""
        outfile = Path(self.tmp_dir, "params-file-invalid.yml")
        builder = ParamsFileBuilder(self.invalid_template_schema)
        res = builder.write_params_file(str(outfile))

        assert res is False
        assert "Pipeline schema file is invalid" in caplog.text

    def test_build_template_file_exists(self, caplog):
        """Build a schema from a template"""

        # Creates a new empty file
        outfile = Path(self.tmp_dir) / "params-file.yml"
        with open(outfile, "w"):
            pass

        res = self.params_template_builder.write_params_file(outfile)

        assert res is False
        assert f"File '{outfile}' exists!" in caplog.text

        outfile.unlink()
