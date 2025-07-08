from unittest.mock import MagicMock, patch

from nf_core.subworkflows._completion import autocomplete_subworkflows


class DummyParam:
    # Minimal mock object for Click parameter (not used in the function)
    pass


class DummyCtx:
    def __init__(self, obj=None):
        self.obj = obj


@patch("nf_core.subworkflows._completion.CompletionItem")
@patch("nf_core.subworkflows._completion.ModuleList")
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
