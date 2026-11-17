"""Snippet tests for the ast-grep Python-API matchers used by pipeline lint checks.

Each matcher takes the root node of a parsed Nextflow file and yields the
offending nodes: ``valid`` snippets must yield nothing, ``invalid`` snippets
at least one node.
"""

import re

import pytest
from ast_grep_py import SgRoot

from nf_core import astgrep
from nf_core.pipelines.lint.pipeline_if_empty_null import find_if_empty_null
from nf_core.pipelines.lint.pipeline_todos import find_todo_comments
from nf_core.pipelines.lint.system_exit import find_system_exit

pytestmark = pytest.mark.skipif(not astgrep.nextflow_available(), reason="tree-sitter-nextflow parser not available")

CASES = {
    find_if_empty_null: {
        "valid": [
            "ch.ifEmpty([])",
            'ch.ifEmpty { error "empty samplesheet" }',
            "workflow {\n    // ifEmpty(null) in a comment is fine\n    ch_ok = ch.toList()\n}\n",
            "foo(ifEmpty, null)",
        ],
        "invalid": [
            "ch.ifEmpty(null)",
            "ch.ifEmpty( null )",
            "Channel.fromPath(params.input).ifEmpty(null)",
            "ch.map { it }.ifEmpty(null)",
            "ch.ifEmpty(\n    null\n)\n",
            "ch | ifEmpty(null)",
        ],
    },
    find_system_exit: {
        "valid": [
            "System.exit(0)",
            "// System.exit(1) in a comment is fine",
            'error "Something went wrong"',
        ],
        "invalid": [
            "System.exit(1)",
            "System.exit(status)",
            "class Utils {\n    public static void fail(msg) {\n        log.error(msg)\n        System.exit(1)\n    }\n}\n",
        ],
    },
    find_todo_comments: {
        "valid": [
            "// a regular comment",
            'println "TODO nf-core: inside a string is not a template TODO"',
        ],
        "invalid": [
            "// TODO nf-core: edit this section",
            "/*\n * TODO nf-core: a block comment TODO\n */\n",
            'process FOO {\n    script:\n    // TODO nf-core: replace the command below\n    """\n    echo hi\n    """\n}\n',
        ],
    },
}


def _params(kind):
    return [
        pytest.param(matcher, snippet, id=f"{matcher.__name__}-{i}")
        for matcher, cases in CASES.items()
        for i, snippet in enumerate(cases[kind])
    ]


def _matches(matcher, snippet):
    # match even if the snippet has parse errors (lint itself would fall back to regex for those)
    return list(matcher(SgRoot(snippet, "nextflow").root()))


@pytest.mark.parametrize(("matcher", "snippet"), _params("valid"))
def test_valid_snippet_not_flagged(matcher, snippet):
    assert not _matches(matcher, snippet)


@pytest.mark.parametrize(("matcher", "snippet"), _params("invalid"))
def test_invalid_snippet_flagged(matcher, snippet):
    assert _matches(matcher, snippet)


def test_find_nodes_falls_back_to_regex_on_parse_errors(tmp_path):
    """A file the grammar cannot parse is still scanned, line by line."""
    nf_file = tmp_path / "broken.nf"
    nf_file.write_text("process {{{ \nch.ifEmpty(null)\n")
    assert astgrep.parse(nf_file.read_text()) is None
    matches = list(astgrep.find_nodes(find_if_empty_null, [nf_file], fallback=re.compile(r"ifEmpty\s*\(\s*null\s*\)")))
    assert matches == [(nf_file, 2, "ch.ifEmpty(null)")]
