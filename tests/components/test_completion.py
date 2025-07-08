from unittest.mock import MagicMock, patch

import pytest

from nf_core.components.components_completion import autocomplete_modules, autocomplete_subworkflows, autocomplete_pipelines

class DummyParam:
    # Minimal mock object for Click parameter (not used in the function)
    pass


class DummyCtx:
    def __init__(self, obj=None, params=None):
        self.obj = obj
        self.params = params if params is not None else {}

def test_autocomplete_modules():
    ctx = DummyCtx()
    param = DummyParam()
    completions = autocomplete_modules(ctx, param, "bcf")

    values = [c.value for c in completions]
    assert "bcftools/call" in values
    assert "fastqc" not in values

@patch("nf_core.components.components_completion.CompletionItem")
@patch("nf_core.components.components_completion.ModuleList")
def test_autocomplete_modules_mocked(mock_module_list_class, mock_completion_item_class):
    # Setup mock for module list
    mock_instance = mock_module_list_class.return_value
    mock_instance.modules_repo.get_avail_components.return_value = ["fastqc", "bcftools/call", "bcftools/index"]

    # Setup mock for CompletionItem
    def mock_completion(value):
        mock_item = MagicMock()
        mock_item.value = value
        return mock_item

    mock_completion_item_class.side_effect = mock_completion

    ctx = DummyCtx()
    param = DummyParam()
    completions = autocomplete_modules(ctx, param, "bcf")

    values = [c.value for c in completions]
    assert "bcftools/call" in values
    assert "fastqc" not in values


@patch("nf_core.components.components_completion.ModuleList")
def test_autocomplete_modules_with_ctx_obj(mock_module_list_class):
    # Setup mock return value
    mock_instance = mock_module_list_class.return_value
    mock_instance.modules_repo.get_avail_components.return_value = ["custommodule/a", "custommodule/b", "othermodule/x"]

    # Provide ctx.obj with custom values
    ctx = DummyCtx(
        obj={
            "modules_repo_url": "https://custom.url/modules",
            "modules_repo_branch": "custom-branch",
            "modules_repo_no_pull": True,
        }
    )

    param = DummyParam()
    completions = autocomplete_modules(ctx, param, "custom")

    # Assertions
    mock_module_list_class.assert_called_once_with(".", True, "https://custom.url/modules", "custom-branch", True)

    values = [c.value for c in completions]
    assert "custommodule/a" in values
    assert "custommodule/b" in values
    assert "othermodule/x" not in values


def test_autocomplete_modules_missing_argument(capfd):
    ctx = DummyCtx()
    param = DummyParam()

    with pytest.raises(TypeError) as exc_info:
        autocomplete_modules(ctx, param)  # Missing 'incomplete' argument

    assert "missing 1 required positional argument" in str(exc_info.value)


def test_autocomplete_subworkflows():
    ctx = DummyCtx()
    param = DummyParam()
    completions = autocomplete_subworkflows(ctx, param, "utils")
    print(completions)

    values = [c.value for c in completions]
    assert "utils_nextflow_pipeline" in values
    assert "vcf_gather_bcftools" not in values

@patch("nf_core.components.components_completion.CompletionItem")
@patch("nf_core.components.components_completion.SubworkflowList")
def test_autocomplete_subworkflows_mocked(mock_subworkflows_list_class, mock_completion_item_class):
    # Setup mock for module list
    mock_instance = mock_subworkflows_list_class.return_value
    mock_instance.modules_repo.get_avail_components.return_value = [
        "vcf_gather_bcftools",
        "fastq_align_star",
        "utils_nextflow_pipeline",
    ]

    # Setup mock for CompletionItem
    def mock_completion(value):
        mock_item = MagicMock()
        mock_item.value = value
        return mock_item

    mock_completion_item_class.side_effect = mock_completion

    ctx = DummyCtx()
    param = DummyParam()
    completions = autocomplete_subworkflows(ctx, param, "utils")

    values = [c.value for c in completions]
    assert "utils_nextflow_pipeline" in values
    assert "vcf_gather_bcftools" not in values


@patch("nf_core.components.components_completion.SubworkflowList")
def test_autocomplete_subworkflows_with_ctx_obj(mock_subworkflows_list_class):
    # Setup mock return value
    mock_instance = mock_subworkflows_list_class.return_value
    mock_instance.modules_repo.get_avail_components.return_value = [
        "vcf_gather_bcftools",
        "fastq_align_star",
        "utils_nextflow_pipeline",
    ]

    # Provide ctx.obj with custom values
    ctx = DummyCtx(
        obj={
            "modules_repo_url": "https://custom.url/modules",
            "modules_repo_branch": "custom-branch",
            "modules_repo_no_pull": True,
        }
    )

    param = DummyParam()
    completions = autocomplete_subworkflows(ctx, param, "utils")

    # Assertions
    mock_subworkflows_list_class.assert_called_once_with(".", True, "https://custom.url/modules", "custom-branch", True)

    values = [c.value for c in completions]
    assert "utils_nextflow_pipeline" in values
    assert "vcf_gather_bcftools" not in values


def test_autocomplete_subworkflows_missing_argument():
    ctx = DummyCtx()
    param = DummyParam()

    with pytest.raises(TypeError) as exc_info:
        autocomplete_subworkflows(ctx, param)  # Missing 'incomplete' argument

    assert "missing 1 required positional argument" in str(exc_info.value)

def test_autocomplete_pipelines():
    ctx = DummyCtx()
    param = DummyParam()
    completions = autocomplete_pipelines(ctx, param, "next")

    values = [c.value for c in completions]
    assert "nextflow-io/hello" in values
    assert "nf-core/rnasek" not in values

@patch("nf_core.components.components_completion.Workflows")
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
