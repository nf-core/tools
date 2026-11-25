import json
from pathlib import Path
from unittest import mock

import pytest
import yaml

from nf_core.pipelines.params_file import ParamsFileBuilder

from ..test_pipelines import TestPipelines


class TestParamsFileBuilder(TestPipelines):
    """Class for schema tests"""

    def setUp(self):
        """Create a new PipelineSchema object"""
        super().setUp()

        self.template_schema = Path(self.pipeline_dir, "nextflow_schema.json")
        self.params_template_builder = ParamsFileBuilder(self.pipeline_dir)
        self.outfile = Path(self.pipeline_dir, "params-file.yml")

    def test_build_template(self):
        self.params_template_builder.write_params_file(self.outfile)

        assert self.outfile.exists()

        with open(self.outfile) as fh:
            out = fh.read()

        assert f"{self.pipeline_obj.pipeline_prefix}/{self.pipeline_obj.pipeline_name}" in out

    def test_build_template_invalid_schema(self):
        """Build a schema from a template"""
        schema = {}
        with open(self.template_schema) as fh:
            schema = json.load(fh)
            del schema["allOf"]

        with open(self.template_schema, "w") as fh:
            json.dump(schema, fh)

        builder = ParamsFileBuilder(self.template_schema)
        res = builder.write_params_file(self.outfile)

        assert res is False
        assert "Pipeline schema file is invalid" in self.caplog.text

    def test_build_template_file_exists(self):
        """Build a schema from a template"""

        # Creates a new empty file
        self.outfile.touch()

        res = self.params_template_builder.write_params_file(self.outfile)

        assert res is False
        assert f"File '{self.outfile}' exists!" in self.caplog.text

        self.outfile.unlink()

    def test_build_template_content(self):
        """Test that the content of the params file is correct"""
        self.params_template_builder.write_params_file(self.outfile)

        with open(self.outfile) as fh:
            out = fh.read()

        assert f"{self.pipeline_obj.pipeline_prefix}/{self.pipeline_obj.pipeline_name}" in out
        assert "# input: null" in out


@pytest.mark.parametrize(
    "schema_uri,defs,plugin",
    [
        # Draft 7 schema used by nf-validation
        ("https://json-schema.org/draft-07/schema", "definitions", "nf-validation"),
        # Draft 2020-12 schema used by nf-schema
        ("https://json-schema.org/draft/2020-12/schema", "$defs", "nf-schema"),
    ],
)
@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("show_hidden", [False, True])
def test_build_template_ungrouped(tmp_path, schema_uri, defs, plugin, grouped, show_hidden):
    """Keep ungrouped defaults, descriptions, required flags and hidden handling"""
    schema = {
        "$schema": schema_uri,
        "properties": {
            "input": {"type": "string", "default": "reads.csv", "description": "Input samplesheet"},
            "hidden_count": {"type": "integer", "default": 2, "hidden": True},
        },
        "required": ["input"],
    }
    # threads is always in the config but only in the schema when grouped, so it must only appear then
    config = {
        "plugins": [f"{plugin}@1.0.0"],
        "manifest": {"name": "example/pipeline", "version": "1.0.0"},
        "params": {"input": "reads.csv", "hidden_count": 2, "threads": 4},
    }
    if grouped:
        schema[defs] = {
            "resources": {"title": "Resources", "properties": {"threads": {"type": "integer", "default": 4}}}
        }
        schema["allOf"] = [{"$ref": f"#/{defs}/resources"}]
    Path(tmp_path, "nextflow_schema.json").write_text(json.dumps(schema))
    outfile = Path(tmp_path, "params-file.yml")

    with mock.patch("nf_core.utils.fetch_wf_config", return_value=config):
        assert ParamsFileBuilder(tmp_path).write_params_file(outfile, show_hidden=show_hidden)

    content = outfile.read_text()
    parameters = yaml.safe_load("\n".join(line[2:] for line in content.splitlines() if line.startswith("# ")))
    expected = {"input": "reads.csv"}
    if grouped:
        expected["threads"] = 4
    if show_hidden:
        expected["hidden_count"] = 2
    assert parameters == expected
    assert "Input samplesheet" in content
    assert "Required" in content
