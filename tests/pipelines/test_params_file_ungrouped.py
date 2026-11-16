"""Parameter templates must include both supported schema property locations."""

import json
from unittest import mock

import pytest
import yaml

from nf_core.pipelines.params_file import ParamsFileBuilder


@pytest.mark.parametrize(
    ("draft", "defs", "plugin"),
    [
        ("https://json-schema.org/draft-07/schema", "definitions", "nf-validation"),
        ("https://json-schema.org/draft/2020-12/schema", "$defs", "nf-schema"),
    ],
)
@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("show_hidden", [False, True])
def test_write_params_file_includes_ungrouped(tmp_path, draft, defs, plugin, grouped, show_hidden):
    """Keep ungrouped defaults, descriptions, required flags and hidden handling."""
    schema = {
        "$schema": draft,
        "properties": {
            "input": {"type": "string", "default": "reads.csv", "description": "Input samplesheet"},
            "hidden_count": {"type": "integer", "default": 2, "hidden": True},
        },
        "required": ["input"],
    }
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
    (tmp_path / "nextflow_schema.json").write_text(json.dumps(schema))
    output = tmp_path / "params.yml"

    with (
        mock.patch("nf_core.pipelines.list.Workflows.get_remote_workflows"),
        mock.patch("nf_core.utils.fetch_wf_config", return_value=config),
    ):
        builder = ParamsFileBuilder(tmp_path, no_prompts=True)
        assert builder.write_params_file(output, show_hidden=show_hidden)

    content = output.read_text()
    parameters = yaml.safe_load("\n".join(line[2:] for line in content.splitlines() if line.startswith("# ")))
    expected = {"input": "reads.csv"}
    if grouped:
        expected["threads"] = 4
    if show_hidden:
        expected["hidden_count"] = 2
    assert parameters == expected
    assert "Input samplesheet" in content
    assert "Required" in content
