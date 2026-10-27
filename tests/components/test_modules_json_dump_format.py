"""Regression tests for uniform modules.json formatting across commands."""

import json
from pathlib import Path
from unittest import mock

from nf_core.modules.modules_json import ModulesJson


def test_modules_json_dump_formats_by_default(tmp_path: Path) -> None:
    modules_json = ModulesJson(tmp_path)
    modules_json.modules_json = {
        "name": "demo",
        "homePage": "",
        "repos": {"https://z.example": {}, "https://a.example": {}},
    }
    with mock.patch("nf_core.modules.modules_json.dump_json_with_prettier") as formatter:
        modules_json.dump()
    formatter.assert_called_once()
    args = formatter.call_args.args
    assert args[0] == tmp_path / "modules.json"
    assert list(args[1]["repos"]) == ["https://a.example", "https://z.example"]


def test_modules_json_dump_allows_explicit_unformatted_write(tmp_path: Path) -> None:
    modules_json = ModulesJson(tmp_path)
    modules_json.modules_json = {"name": "demo", "homePage": "", "repos": {}}
    with mock.patch("nf_core.modules.modules_json.dump_json_with_prettier") as formatter:
        modules_json.dump(run_prettier=False)
    formatter.assert_not_called()
    assert json.loads((tmp_path / "modules.json").read_text())["name"] == "demo"
