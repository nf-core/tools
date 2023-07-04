import json
import os
import shutil
import tempfile
from pathlib import Path

import nf_core.create
import nf_core.schema
from nf_core.params_template import ParamsFileTemplateBuilder


class TestParamsTemplateBuilder:
    """Class for schema tests"""

    def setup_class(self):
        """Create a new PipelineSchema object"""
        self.schema_obj = nf_core.schema.PipelineSchema()
        self.root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

        # Create a test pipeline in temp directory
        self.tmp_dir = tempfile.mkdtemp()
        self.template_dir = os.path.join(self.tmp_dir, "wf")
        create_obj = nf_core.create.PipelineCreate(
            "testpipeline", "", "", outdir=self.template_dir, no_git=True, plain=True
        )
        create_obj.init_pipeline()

        self.template_schema = os.path.join(self.template_dir, "nextflow_schema.json")
        self.params_template_builder = ParamsFileTemplateBuilder(self.template_dir)

    def teardown_class(self):
        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def test_build_template(self):
        outfile = os.path.join(self.tmp_dir, "params-file.yml")
        self.params_template_builder.write_template(outfile)

        assert os.path.exists(outfile)

        with open(outfile, "r") as fh:
            out = fh.read()

        assert "nf-core/testpipeline" in out

    def test_build_template_invalid_schema(self, caplog):
        """Build a schema from a template"""
        outfile = os.path.join(self.tmp_dir, "params-file.yml")
        schema_path = Path(self.template_schema)
        invalid_schema_file = shutil.copy(self.template_schema, Path(self.template_schema).name + "_invalid.json")

        # Remove the allOf section to make the schema invalid
        with open(invalid_schema_file, "r") as fh:
            o = json.load(fh)
            del o["allOf"]

        with open(invalid_schema_file, "w") as fh:
            json.dump(o, fh)

        builder = ParamsFileTemplateBuilder(invalid_schema_file)
        res = builder.write_template(outfile)

        assert res is False
        assert "Pipeline schema file is invalid" in caplog.text

    def test_build_template_file_exists(self, caplog):
        """Build a schema from a template"""

        # Creates a new empty file
        outfile = Path(self.tmp_dir) / "params-file.yml"
        with open(outfile, "w") as fp:
            pass

        res = self.params_template_builder.write_template(outfile)

        assert res is False
        assert f"File '{outfile}' exists!" in caplog.text

        outfile.unlink()
