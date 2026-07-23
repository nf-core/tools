"""Tests for nf_core.astgrep parser discovery and registration."""

from pathlib import Path
from unittest import mock

from nf_core import astgrep


def test_nextflow_available_bad_library_falls_back():
    """A discovered library without the parser symbol must disable astgrep, not crash.

    Regression: an outdated tree-sitter-nextflow wheel (without the exported
    tree_sitter_nextflow symbol) made nextflow_available() raise RuntimeError,
    crashing lint instead of falling back to regex matching.
    """
    bogus_lib = Path(astgrep.__file__)  # a real file that is not a parser library
    astgrep.nextflow_available.cache_clear()
    try:
        with mock.patch("nf_core.astgrep._find_library", return_value=bogus_lib):
            assert astgrep.nextflow_available() is False
    finally:
        astgrep.nextflow_available.cache_clear()
