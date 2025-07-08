from unittest.mock import MagicMock, patch

import pytest

from nf_core.pipelines._completion import autocomplete_pipelines


class DummyParam:
    pass


class DummyCtx:
    def __init__(self, obj=None):
        self.obj = obj


@patch("nf_core.pipelines._completion.Workflows")
def test_autocomplete_pipelines_mocked(mock_workflows_class):
    # Mock instance
    mock_instance = mock_workflows_class.return_value

    # Mock local and remote workflows
    mock_instance.local_workflows = [MagicMock(full_name="awesome/localpipeline")]
    mock_instance.remote_workflows = [MagicMock(full_name="awesome-remote"), MagicMock(full_name="other-remote")]

    ctx = DummyCtx()
    param = DummyParam()

    completions = autocomplete_pipelines(ctx, param, "awesome")

    # Extract values from CompletionItem
    values = [c.value for c in completions]

    # Assertions
    assert "awesome/localpipeline" in values
    assert "awesome-remote" in values
    assert "other-remote" not in values


def test_autocomplete_pipelines_missing_argument(capfd):
    ctx = DummyCtx()
    param = DummyParam()

    with pytest.raises(TypeError) as exc_info:
        autocomplete_pipelines(ctx, param)  # Missing 'incomplete' argument

    assert "missing 1 required positional argument" in str(exc_info.value)
