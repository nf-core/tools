"""Tests for nf_core.astgrep rule loading and structural/regex matching."""

import logging
from pathlib import Path
from unittest import mock

import pytest
import yaml

from nf_core import astgrep

RULES = sorted(Path(astgrep.__file__).parent.glob("*/lint/rules/*.yml"))
needs_parser = pytest.mark.skipif(not astgrep.nextflow_available(), reason="tree-sitter-nextflow parser not available")

SYSTEM_EXIT_RULE = {
    "id": "test_system_exit",
    "language": "nextflow",
    "message": "System.exit",
    "metadata": {"fallback-regex": r"System\.exit\s*\((?!\s*0\s*\))"},
    "rule": {"pattern": "System.exit($CODE)"},
    "constraints": {"CODE": {"not": {"regex": "^0$"}}},
}
TODO_RULE = {
    "id": "test_todos",
    "language": "nextflow",
    "message": "TODO",
    "metadata": {"fallback-regex": "TODO nf-core"},
    "rule": {"regex": "TODO nf-core", "any": [{"kind": "line_comment"}, {"kind": "block_comment"}]},
}


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def test_find_library_env_override(tmp_path, monkeypatch):
    lib = _write(tmp_path, "libnextflow.so", "")
    monkeypatch.setenv("NFCORE_TREE_SITTER_NEXTFLOW_LIB", str(lib))
    assert astgrep._find_library() == lib


@pytest.mark.parametrize("rule_path", RULES, ids=[p.stem for p in RULES])
@needs_parser
def test_rule_files_compile(rule_path):
    """Every shipped rule must be valid for the installed grammar (unknown node kinds raise RuntimeError)."""
    rule = astgrep.load_rule(rule_path)
    list(astgrep.scan("workflow {}", rule))


def test_load_rule_requires_keys(tmp_path):
    rule = {k: v for k, v in SYSTEM_EXIT_RULE.items() if k != "rule"}
    path = _write(tmp_path, "rule_without_rule.yml", yaml.safe_dump(rule))
    with pytest.raises(ValueError, match="rule"):
        astgrep.load_rule(path)


def test_load_rule_requires_nextflow_language(tmp_path):
    path = _write(tmp_path, "groovy_rule.yml", yaml.safe_dump(dict(SYSTEM_EXIT_RULE, language="groovy")))
    with pytest.raises(ValueError, match="language: nextflow"):
        astgrep.load_rule(path)


@needs_parser
@pytest.mark.parametrize(
    "source, broken",
    [
        ("workflow { foo(1) }", False),
        ("workflow { foo(1 }", True),  # MISSING node only, no ERROR node
        ("process FOO {\n  output:\n  path 'x'\n  script:\n  '''\n", True),
    ],
    ids=["clean", "missing-only", "unterminated-script"],
)
def test_has_parse_errors(source, broken):
    assert astgrep.has_parse_errors(source) is broken


@needs_parser
def test_structural_match_skips_strings_and_allows_exit_zero(tmp_path):
    nf = _write(tmp_path, "main.nf", 'workflow {\n  log.info "System.exit(1)"\n  System.exit(0)\n  System.exit(1)\n}\n')
    assert [(line, text) for _, line, text in astgrep.find_matches(SYSTEM_EXIT_RULE, [nf])] == [(4, "System.exit(1)")]


@needs_parser
def test_parse_error_falls_back_to_regex(tmp_path):
    nf = _write(tmp_path, "broken.nf", 'workflow {\n  log.info "System.exit(1)"\n  foo(1\n}\n')
    assert [line for _, line, _ in astgrep.find_matches(SYSTEM_EXIT_RULE, [nf])] == [2]


@needs_parser
def test_invalid_rule_warns_once_and_uses_regex(tmp_path, caplog):
    rule = dict(SYSTEM_EXIT_RULE, id="test_invalid_kind", rule={"kind": "no_such_kind"})
    files = [_write(tmp_path, f"{i}.nf", "workflow { System.exit(1) }\n") for i in range(3)]
    with caplog.at_level(logging.WARNING, logger="nf_core.astgrep"):
        assert len(list(astgrep.find_matches(rule, files))) == 3
    assert sum("test_invalid_kind" in r.message for r in caplog.records) == 1


@pytest.mark.parametrize("parser_available", [True, False], ids=["structural", "regex"])
def test_non_nextflow_files_same_in_both_modes(tmp_path, parser_available):
    if parser_available and not astgrep.nextflow_available():
        pytest.skip("tree-sitter-nextflow parser not available")
    md = _write(tmp_path, "README.md", "<!-- TODO nf-core: fill in -->\nSystem.exit(1)\n")
    with mock.patch("nf_core.astgrep.nextflow_available", return_value=parser_available):
        assert list(astgrep.find_matches(SYSTEM_EXIT_RULE, [md])) == []
        assert [line for _, line, _ in astgrep.find_matches(TODO_RULE, [md], regex_unparseable=True)] == [1]
