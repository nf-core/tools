from pathlib import Path

import pytest

from nf_core.components import records
from nf_core.components.nfcore_component import NFCoreComponent

TYPED_MODULE = Path(__file__).parents[1] / "data" / "typed_module" / "preseq_lcextrap"


@pytest.mark.parametrize(
    "main_nf,expected",
    [
        ("nextflow.enable.types = true\nprocess FOO {}", True),
        ("  nextflow.enable.types=true // comment\n", True),
        ("nextflow.enable.types = false\n", False),
        ("// nextflow.enable.types = true\n", False),
        ("process FOO {}", False),
    ],
)
def test_is_typed(main_nf, expected):
    assert records.is_typed(main_nf) is expected


@pytest.mark.parametrize(
    "entry,expected",
    [
        ({"type": "record", "fields": {}}, True),
        ({"type": {"type": "string"}}, False),
        ({"meta": {"type": "map"}}, False),
        ([{"meta": {}}, {"bam": {}}], False),
    ],
)
def test_is_record(entry, expected):
    assert records.is_record(entry) is expected


def test_strip_comments_keeps_slashes_in_strings():
    assert records.strip_comments("version: eval(\"sed -n 's/Version: //p'\") // trailing") == (
        "version: eval(\"sed -n 's/Version: //p'\") "
    )


def test_input_record_types_and_optional_flags():
    found = records.find_records(
        """
    // a comment with record(foo: Bar)
    record(
        id: String,
        meta: Record?,
        reads: Map<String, Path>,
        index: Set < Path >?,  // trailing comment
        tool_args: String?
    )
    """
    )
    assert len(found) == 1
    assert records.input_record(found[0][0])["fields"] == {
        "id": {"type": "String", "optional": False},
        "meta": {"type": "Record", "optional": True},
        "reads": {"type": "Map<String,Path>", "optional": False},
        "index": {"type": "Set<Path>", "optional": True},
        "tool_args": {"type": "String", "optional": True},
    }


def test_topic_records_group_by_topic():
    topics = records.topic_records(
        """
    record(process: "${task.process}", tool: 'perl', version: eval("perl -e 'print substr(\\$^V, 1)'")) >> 'versions'
    record(process: "${task.process}", tool: 'gzip', version: '1.13') >> "versions"
    record(sample: id) >> 'samples'
    """
    )
    assert list(topics) == ["versions", "samples"]
    assert [entry["fields"]["tool"]["value"] for entry in topics["versions"]] == ["'perl'", "'gzip'"]
    assert topics["versions"][0]["fields"]["version"]["value"] == "eval(\"perl -e 'print substr(\\$^V, 1)'\")"


def test_find_records_counts_each_record():
    assert len(records.find_records("record(a: A)\nrecord(b: B)")) == 2
    assert records.find_records("tuple val(meta), path(bam)") == []
    assert records.find_records("myrecord(a: A)") == []


def test_describe_differences():
    expected = [records.normalise_record(records.input_record("id: String, meta: Record?, bam: Path"), "type")]
    found = [
        records.normalise_record(
            {
                "type": "record",
                "fields": {"id": {"type": "String"}, "meta": {"type": "Record"}, "bai": {"type": "Path"}},
            },
            "type",
        )
    ]
    assert records.describe_differences(expected, found) == (
        "missing field(s) `bam`; field(s) not in `main.nf`: `bai`; `meta` should have optional `True`, found `False`"
    )
    assert "found 2 entries" in records.describe_differences(expected, found * 2)


def test_component_parses_typed_module():
    component = NFCoreComponent(
        component_name="preseq/lcextrap",
        repo_url=None,
        component_dir=TYPED_MODULE,
        repo_type="modules",
        base_dir=TYPED_MODULE,
        component_type="modules",
        remote_component=False,
    )
    component.get_inputs_from_main_nf()
    component.get_outputs_from_main_nf()
    component.get_topics_from_main_nf()

    assert component.is_typed
    assert component.inputs == [
        {
            "type": "record",
            "fields": {
                "id": {"type": "String", "optional": False},
                "meta": {"type": "Record", "optional": True},
                "single_end": {"type": "Boolean", "optional": False},
                "bam": {"type": "Path", "optional": False},
                "preseq_lcextrap_args": {"type": "String", "optional": True},
                "output_prefix": {"type": "String", "optional": True},
            },
        }
    ]
    assert component.outputs == [
        {
            "type": "record",
            "fields": {
                "id": {"value": "id"},
                "meta": {"value": "meta"},
                "lc_extrap": {"value": 'file("*.lc_extrap.txt")'},
                "log": {"value": 'file("*.log")'},
            },
        }
    ]
    assert list(component.topics) == ["versions"]
    assert component.topics["versions"][0]["fields"]["version"]["value"] == (
        "eval(\"preseq 2>&1 | sed -n 's/Version: //p'\")"
    )
