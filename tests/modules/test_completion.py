from unittest.mock import MagicMock, patch

from nf_core.modules._completion import autocomplete_modules


class DummyParam:
    # Minimal mock object for Click parameter (not used in the function)
    pass


class DummyCtx:
    def __init__(self, obj=None):
        self.obj = obj


@patch("nf_core.modules._completion.CompletionItem")
@patch("nf_core.modules._completion.ModuleList")
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
