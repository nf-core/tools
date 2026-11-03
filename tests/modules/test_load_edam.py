"""Tests for load_edam() and the EDAM extension map.

The fixture below is a hand-cut slice of EDAM 1.25 — real URIs, labels,
synonyms and "File extension" values, copied verbatim from the release TSV —
so the tests need no network access and no 1.9 MB blob in the repository.
Each row is there for a reason, noted inline.
"""

from pathlib import Path
from unittest import mock

import pytest
import requests

from nf_core.modules.modules_utils import _parse_edam, load_edam, load_edam_with_status

# Columns used by the parser, at their EDAM.tsv positions. The real file has
# 86 columns; the fixture pads to 15 so index 14 ("File extension") lands right.
HEADER = ["Class ID", "Preferred Label", "Synonyms"] + [f"c{i}" for i in range(3, 14)] + ["File extension"]

ROWS = [
    # curated column populated — the only source upstream ever used
    ("format_1930", "FASTQ", "FASTAQ|fq", "fq|fastq"),
    # common formats with an EMPTY curated column: the gap this change closes
    ("format_2572", "BAM", "", ""),
    ("format_1929", "FASTA", "FASTA sequence format|FASTA format", ""),
    ("format_3016", "VCF", "", ""),
    ("format_3003", "BED", "", ""),
    ("format_3462", "CRAM", "", ""),
    # 'pir' is claimed by two format concepts -> must be dropped, not guessed
    ("format_1948", "nbrf/pir", "nbrf|pir", ""),
    ("format_1976", "pir", "", ""),
    # 'xlsx' is curated on one concept and the preferred label of another;
    # the curated column has to win
    ("format_3977", "ObjTables", "", "xlsx"),
    ("format_3620", "xlsx", "", ""),
    # a non-format concept, to prove the format_* filter holds
    ("data_0006", "Data", "Data record|Data set|Datum", ""),
]


def _tsv() -> bytes:
    lines = ["\t".join(HEADER)]
    for uri_id, label, syn, ext in ROWS:
        row = [f"http://edamontology.org/{uri_id}", label, syn] + [""] * 11 + [ext]
        lines.append("\t".join(row))
    return ("\n".join(lines) + "\n").encode("utf-8")


@pytest.fixture
def tsv_bytes():
    return _tsv()


@pytest.fixture
def edam_map(tsv_bytes):
    return _parse_edam(tsv_bytes)


# --------------------------------------------------------------- load_edam()
def test_failed_download_is_signalled(tmp_path):
    """A network failure must be distinguishable from an empty ontology."""
    with mock.patch.object(requests, "get", side_effect=requests.exceptions.ConnectionError("offline")):
        mapping, ok = load_edam_with_status(tmp_path)
    assert mapping == {}
    assert ok is False


def test_successful_load_is_signalled(tmp_path, tsv_bytes):
    (tmp_path / "EDAM.tsv").write_bytes(tsv_bytes)
    mapping, ok = load_edam_with_status(tmp_path)
    assert ok is True
    assert mapping["bam"][0].endswith("format_2572")


def test_unreadable_cache_is_signalled(tmp_path):
    """An OSError on the cached file is a failure, not an empty answer."""
    (tmp_path / "EDAM.tsv").write_bytes(b"")
    with mock.patch.object(Path, "read_bytes", side_effect=OSError("boom")):
        mapping, ok = load_edam_with_status(tmp_path)
    assert mapping == {}
    assert ok is False


def test_download_is_cached(tmp_path, tsv_bytes):
    """A successful download is written to the cache directory."""
    response = mock.Mock(content=tsv_bytes)
    response.raise_for_status = mock.Mock()
    with mock.patch.object(requests, "get", return_value=response) as get:
        mapping, ok = load_edam_with_status(tmp_path)
    assert ok is True
    assert get.call_count == 1
    assert (tmp_path / "EDAM.tsv").read_bytes() == tsv_bytes


# -------------------------------------------------------------- _parse_edam()
@pytest.mark.parametrize(
    "extension,concept",
    [
        ("bam", "format_2572"),
        ("fasta", "format_1929"),
        ("vcf", "format_3016"),
        ("bed", "format_3003"),
        ("cram", "format_3462"),
    ],
)
def test_formats_without_a_curated_extension_still_resolve(edam_map, extension, concept):
    """These have an empty "File extension" column, so keying on it alone missed them."""
    assert edam_map[extension][0].endswith(concept)


def test_curated_extension_column_is_still_used(edam_map):
    assert edam_map["fq"][0].endswith("format_1930")
    assert edam_map["fastq"][0].endswith("format_1930")


def test_curated_column_wins_over_a_label(edam_map):
    """'xlsx' is curated on format_3977 and the preferred label of format_3620."""
    assert edam_map["xlsx"][0].endswith("format_3977")


def test_ambiguous_token_is_dropped(edam_map):
    """'pir' is claimed by format_1948 and format_1976, so it must not be emitted."""
    assert "pir" not in edam_map
    assert edam_map["nbrf"][0].endswith("format_1948")


def test_non_format_concepts_are_ignored(edam_map):
    assert "data" not in edam_map
    assert not any(uri.endswith("data_0006") for uri, _ in edam_map.values())


def test_values_are_uri_and_label(edam_map):
    uri, label = edam_map["bam"]
    assert uri == "http://edamontology.org/format_2572"
    assert label == "BAM"


def _extract_add_edam_ontologies():
    """Pull the nested helper out of ModuleLint.update_meta_yml_file so the
    guard can be exercised without a full lint run."""
    import inspect
    import logging
    import re
    import textwrap

    import ruamel.yaml

    from nf_core.modules.lint import ModuleLint

    src = inspect.getsource(ModuleLint.update_meta_yml_file)
    lines = src.splitlines()
    start = next(i for i, line in enumerate(lines) if "def _add_edam_ontologies" in line)
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        end = i + 1
    namespace: dict = {"re": re, "ruamel": ruamel, "log": logging.getLogger(__name__)}
    exec(compile(textwrap.dedent("\n".join(lines[start:end])), "<_add_edam_ontologies>", "exec"), namespace)
    return namespace["_add_edam_ontologies"]


def test_add_edam_ontologies_signature_matches_call_sites():
    """`edam_ok` must sit where update_meta_yml_file actually passes it.

    The four call sites pass positionally as
    (section, edam_formats, edam_ok, desc). If the signature declares
    (section, edam_formats, desc, edam_ok) instead, `edam_ok` receives a
    non-empty description string -- always truthy -- and the guard below
    silently stops guarding.
    """
    import inspect
    import re

    from nf_core.modules.lint import ModuleLint

    src = inspect.getsource(ModuleLint.update_meta_yml_file)
    signature = re.search(r"def _add_edam_ontologies\(([^)]*)\)", src).group(1)
    params = [p.strip().split("=")[0].strip() for p in signature.split(",")]
    assert params == ["section", "edam_formats", "edam_ok", "desc"], (
        f"signature is {params}; the call sites pass edam_ok third, so edam_ok must be the third parameter"
    )


def test_failed_load_leaves_ontologies_untouched():
    """A failed ontology load must not write `ontologies: []`."""
    add_edam_ontologies = _extract_add_edam_ontologies()
    section = {"type": "file", "description": "BAM file", "pattern": "*.{bam}"}
    add_edam_ontologies(section, {}, False, "input - bam")
    assert "ontologies" not in section, (
        f"edam_ok=False still wrote {section.get('ontologies')!r}; a failed "
        f"download is being recorded as 'this file has no ontology'"
    )


def test_successful_load_still_annotates():
    """The guard must not block annotation when the ontology did load."""
    add_edam_ontologies = _extract_add_edam_ontologies()
    section = {"type": "file", "description": "BAM file", "pattern": "*.{bam}"}
    add_edam_ontologies(section, {"bam": ("http://edamontology.org/format_2572", "BAM")}, True, "input - bam")
    assert [dict(o)["edam"] for o in section["ontologies"]] == ["http://edamontology.org/format_2572"]


def test_load_edam_returns_plain_dict(tmp_path, tsv_bytes):
    """load_edam() must stay dict-returning — upstream test_modules_utils.py
    calls it with no argument and does edam_formats.items()."""
    (tmp_path / "EDAM.tsv").write_bytes(tsv_bytes)
    with mock.patch("nf_core.modules.modules_utils.NFCORE_CACHE_DIR", str(tmp_path)):
        result = load_edam()
    assert isinstance(result, dict)
    first_key, first_value = next(iter(result.items()))
    assert isinstance(first_key, str)
    assert isinstance(first_value, tuple)
    assert len(first_value) == 2


def test_load_edam_accepts_no_argument(tmp_path):
    """Signature must remain callable with zero arguments."""
    import inspect

    sig = inspect.signature(load_edam)
    for param in sig.parameters.values():
        assert param.default is not inspect.Parameter.empty, (
            f"load_edam parameter {param.name!r} has no default; upstream calls load_edam() with no arguments"
        )
