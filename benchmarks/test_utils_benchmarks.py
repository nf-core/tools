"""CodSpeed performance benchmarks for nf_core.utils helpers.

These benchmarks focus on pure, CPU-bound utility functions that run on the hot
path of many nf-core commands (config parsing, schema handling, hashing, string
processing). They avoid network and subprocess calls so they stay deterministic
under CodSpeed's simulation instrument.
"""

import pytest

import nf_core.utils


@pytest.fixture
def large_nested_dict():
    """Build a deeply nested, unsorted dictionary for sorting benchmarks."""
    d = {}
    for i in range(200):
        d[f"key_{200 - i:03d}"] = {
            f"sub_{j:03d}": {f"leaf_{k:03d}": f"value_{i}_{j}_{k}" for k in range(10)} for j in range(10)
        }
    return d


@pytest.fixture
def ansi_string():
    """A long string interleaved with ANSI escape sequences."""
    chunk = "ls \x1b[00m\x1b[01;31mexamplefile.zip\x1b[00m\x1b[01;31m some plain text\n"
    return chunk * 2000


@pytest.fixture
def md5_file(tmp_path):
    """A moderately sized file to hash."""
    fn = tmp_path / "payload.bin"
    fn.write_bytes(b"nf-core benchmark payload\n" * 100_000)
    return fn


def test_strip_ansi_codes(benchmark, ansi_string):
    result = benchmark(nf_core.utils.strip_ansi_codes, ansi_string)
    assert "\x1b" not in result


def test_sort_dictionary(benchmark, large_nested_dict):
    result = benchmark(nf_core.utils.sort_dictionary, large_nested_dict)
    assert len(result) == len(large_nested_dict)


def test_check_if_outdated(benchmark):
    # Pass remote_version explicitly to keep this offline and deterministic.
    is_outdated, _, _ = benchmark(nf_core.utils.check_if_outdated, "2.0.1", "2.5.0")
    assert is_outdated is True


def test_file_md5(benchmark, md5_file):
    result = benchmark(nf_core.utils.file_md5, md5_file)
    assert isinstance(result, str) and len(result) == 32


def test_nested_setitem(benchmark):
    def run():
        d = {"a": {"b": {"c": "value"}}}
        nf_core.utils.nested_setitem(d, ["a", "b", "c"], "updated")
        return d

    result = benchmark(run)
    assert result["a"]["b"]["c"] == "updated"


def test_unquote(benchmark):
    result = benchmark(nf_core.utils.unquote, "'a fairly long quoted string value'")
    assert result == "a fairly long quoted string value"


def test_plural_helpers(benchmark):
    def run():
        return (
            nf_core.utils.plural_s(3),
            nf_core.utils.plural_y([1, 2]),
            nf_core.utils.plural_es(0),
        )

    result = benchmark(run)
    assert result == ("s", "ies", "es")
