"""Synchronise zero defaults through the offline schema build path."""

import json
from unittest import mock

import pytest

from nf_core.pipelines.schema import PipelineSchema


@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize(("param_type", "value"), [("integer", 0), ("number", 0.0), ("integer", 2)])
def test_build_schema_adds_missing_numeric_default(tmp_path, grouped, param_type, value):
    """Existing numeric properties without defaults must gain the config default."""
    properties = {"threshold": {"type": param_type}}
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema"}
    if grouped:
        schema["$defs"] = {"options": {"properties": properties}}
        schema["allOf"] = [{"$ref": "#/$defs/options"}]
    else:
        schema["properties"] = properties
    schema_path = tmp_path / "nextflow_schema.json"
    schema_path.write_text(json.dumps(schema))
    (tmp_path / "main.nf").write_text("workflow {}\n")
    (tmp_path / "nextflow.config").write_text(f"params.threshold = {value}\n")
    config = {
        "plugins": ["nf-schema@2.7.3"],
        "params": {"threshold": value},
        "manifest": {"name": "example/pipeline"},
    }

    with (
        mock.patch("nf_core.utils.fetch_wf_config", return_value=config),
        mock.patch("nf_core.pipelines.lint_utils.run_prettier_on_file"),
    ):
        assert PipelineSchema().build_schema(tmp_path, no_prompts=True, web_only=False, url=None) is not False

    written = json.loads(schema_path.read_text())
    written_properties = written["$defs"]["options"]["properties"] if grouped else written["properties"]
    assert written_properties["threshold"] == {"type": param_type, "default": value}


@pytest.mark.parametrize("value", [False, None, ""])
def test_sync_does_not_add_empty_defaults(value):
    """Keep the established policy of omitting false, null and empty defaults."""
    schema = PipelineSchema()
    schema.schema = {"properties": {"option": {"type": "boolean" if value is False else "string"}}}
    schema.pipeline_params = {"option": value}
    schema.no_prompts = True
    schema.get_schema_defaults()
    schema.add_schema_found_configs()
    assert "default" not in schema.schema["properties"]["option"]
