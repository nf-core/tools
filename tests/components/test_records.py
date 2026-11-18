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


TYPED_PROCESS = """
nextflow.enable.types = true

process EXAMPLE {
    tag "${id}"

    ext [
        prefix: { output_prefix ?: "${id}" },
        args: { tool_args ?: '' }
    ]

    input:
    // a comment with record(foo: Bar)
    record(
        id: String,
        meta: Record?,
        reads: Map<String, Path>,
        /* a block comment: with a colon */
        index: Set<Path>?,  // trailing comment
        tool_args: String?,
        output_prefix: String?
    )

    output:
    record(id: id, meta: meta, out: file("*.txt", optional: true))

    topic:
    record(process: "${task.process}", tool: 'perl', version: eval("perl -e 'print substr(\\$^V, 1)'")) >> 'versions'
    record(process: "${task.process}", tool: 'gzip', version: '1.13') >> "versions"
    record(sample: id) >> 'samples'

    script:
    \"\"\"
    tool ${task.ext.args} > ${task.ext.prefix}.txt
    \"\"\"
}
"""


def test_parse_input_record_types_and_optional_flags():
    module = records.parse(TYPED_PROCESS)
    assert module.parse_errors == 0
    assert len(module.inputs) == 1
    assert module.inputs[0]["fields"] == {
        "id": {"type": "String", "optional": False},
        "meta": {"type": "Record", "optional": True},
        "reads": {"type": "Map<String,Path>", "optional": False},
        "index": {"type": "Set<Path>", "optional": True},
        "tool_args": {"type": "String", "optional": True},
        "output_prefix": {"type": "String", "optional": True},
    }


def test_parse_output_record_values():
    module = records.parse(TYPED_PROCESS)
    assert len(module.outputs) == 1
    assert module.outputs[0]["fields"] == {
        "id": {"value": "id"},
        "meta": {"value": "meta"},
        "out": {"value": 'file("*.txt", optional: true)'},
    }


def test_parse_topic_records_group_by_topic():
    topics = records.parse(TYPED_PROCESS).topics
    assert list(topics) == ["versions", "samples"]
    assert [entry["fields"]["tool"]["value"] for entry in topics["versions"]] == ["'perl'", "'gzip'"]
    assert topics["versions"][0]["fields"]["version"]["value"] == "eval(\"perl -e 'print substr(\\$^V, 1)'\")"


def test_parse_ext_keys():
    assert records.parse(TYPED_PROCESS).ext == {"prefix", "args"}


def test_parse_counts_each_record():
    two_outputs = TYPED_PROCESS.replace(
        'record(id: id, meta: meta, out: file("*.txt", optional: true))',
        "record(id: id, meta: meta)\n    record(id: id, meta: meta)",
    )
    assert len(records.parse(two_outputs).outputs) == 2


def test_describe_differences():
    expected = [
        records.normalise_record(
            {
                "type": "record",
                "fields": {
                    "id": {"type": "String", "optional": False},
                    "meta": {"type": "Record", "optional": True},
                    "bam": {"type": "Path", "optional": False},
                },
            },
            "type",
        )
    ]
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
