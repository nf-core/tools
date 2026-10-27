"""Verify default modules.json persistence follows the real formatter wrapper."""

import json
from unittest.mock import patch

from nf_core.modules.modules_json import ModulesJson


def test_default_dump_writes_sorted_json_and_calls_prettier(tmp_path):
    modules = ModulesJson(tmp_path)
    modules.modules_json = {
        "name": "demo",
        "homePage": "",
        "repos": {"https://z.example": {}, "https://a.example": {}},
    }

    # Run the real dump and JSON writer; stub only the external formatter hook.
    with patch("nf_core.pipelines.lint_utils.run_prettier_on_file") as prettier:
        modules.dump()

    result = tmp_path / "modules.json"
    assert result.is_file()
    assert list(json.loads(result.read_text())["repos"]) == ["https://a.example", "https://z.example"]
    prettier.assert_called_once_with(result)
