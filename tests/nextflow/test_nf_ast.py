"""Tests for nf_core.nextflow.nf_ast parser discovery and registration."""

from pathlib import Path
from unittest import mock

from nf_core.nextflow import nf_ast


def test_parser_available_bad_library_falls_back():
    """A discovered library without the parser symbol must disable structural matching, not crash.

    Regression: an outdated tree-sitter-nextflow wheel (without the exported
    tree_sitter_nextflow symbol) made parser_available() raise RuntimeError,
    crashing lint instead of falling back to regex matching.
    """
    bogus_lib = Path(nf_ast.__file__)  # a real file that is not a parser library
    nf_ast.parser_available.cache_clear()
    try:
        with mock.patch("nf_core.nextflow.nf_ast._find_library", return_value=bogus_lib):
            assert nf_ast.parser_available() is False
    finally:
        nf_ast.parser_available.cache_clear()
