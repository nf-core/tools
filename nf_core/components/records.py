"""
Parse the ``record(...)`` declarations of modules that use Nextflow static types
(``nextflow.enable.types = true``).
"""

import re
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from functools import cache
from typing import Any

TYPED_MODULE_RE = re.compile(r"^\s*nextflow\.enable\.types\s*=\s*true\b", re.MULTILINE)


def is_typed(main_nf: str) -> bool:
    """Whether a module enables static types."""
    return TYPED_MODULE_RE.search(main_nf) is not None


def is_record(entry: Any) -> bool:
    """Whether a ``meta.yml`` input, output or topic entry uses the record layout."""
    return isinstance(entry, dict) and entry.get("type") == "record"


@dataclass
class TypedModule:
    """The typed declarations of a module ``main.nf``, as found by the Nextflow grammar."""

    inputs: list[dict] = dataclass_field(default_factory=list)
    outputs: list[dict] = dataclass_field(default_factory=list)
    topics: dict[str, list[dict]] = dataclass_field(default_factory=dict)
    ext: set[str] = dataclass_field(default_factory=set)
    parse_errors: int = 0


def _is_record_call(node) -> bool:
    """Whether a node is a ``record(...)`` call expression."""
    callee = node.child(0)
    return node.kind() == "call_expression" and callee is not None and callee.text() == "record"


def _value_record(call) -> dict:
    """Describe a ``record(...)`` call expression in the ``meta.yml`` record layout."""
    fields = {}
    for argument in call.find_all(kind="named_argument"):
        parent = argument.parent()
        if parent is None or parent.parent() != call:
            continue
        name, *rest = [child for child in argument.children() if child.is_named()]
        fields[name.text()] = {"value": " ".join(rest[0].text().split()) if rest else ""}
    return {"type": "record", "fields": fields}


@cache
def parse(main_nf: str) -> TypedModule:
    """Parse the input, output and topic records and the ``ext`` keys of a typed module."""
    from ast_grep_py import SgRoot

    from nf_core.astgrep import nextflow_available

    if not nextflow_available():
        raise RuntimeError("Linting modules with static types needs ast-grep-py and tree-sitter-nextflow>=0.4.1")
    module = TypedModule()
    root = SgRoot(main_nf, "nextflow").root()
    module.parse_errors = len(root.find_all(kind="ERROR"))

    for record in root.find_all(kind="process_record_input"):
        fields = {}
        for process_input in record.find_all(kind="process_input"):
            name = process_input.find(kind="identifier")
            annotation = process_input.find(kind="type")
            if name is None:
                continue
            type_ = re.sub(r"\s+", "", annotation.text()) if annotation else ""
            fields[name.text()] = {"type": type_.removesuffix("?"), "optional": type_.endswith("?")}
        module.inputs.append({"type": "record", "fields": fields})

    for section in root.find_all(kind="output_section"):
        for call in section.find_all(kind="call_expression"):
            parent = call.parent()
            if _is_record_call(call) and parent is not None and parent.kind() == "expression_statement":
                module.outputs.append(_value_record(call))

    for section in root.find_all(kind="topic_section"):
        for statement in section.find_all(kind="binary_expression"):
            call, *_, target = [child for child in statement.children() if child.is_named()]
            if _is_record_call(call) and target.kind() == "string":
                topic = target.text().strip("'\"")
                module.topics.setdefault(topic, []).append(_value_record(call))

    for statement in root.find_all(kind="command_expression"):
        command = statement.child(0)
        if command is not None and command.text() == "ext":
            for entry in statement.find_all(kind="map_entry"):
                key = entry.child(0)
                if key is not None:
                    module.ext.add(key.text())
    return module


def normalise_record(entry: dict, attribute: str) -> dict:
    """Reduce a record entry to what ``main.nf`` and ``meta.yml`` must agree on.

    ``attribute`` is ``"type"`` for input records, where the type and optional flag
    are compared, and ``"value"`` for output and topic records.
    """
    fields = entry.get("fields")
    if not isinstance(fields, dict):
        return {"record": None}
    normalised = {}
    for name, field in fields.items():
        field = field if isinstance(field, dict) else {}
        if attribute == "type":
            normalised[str(name)] = {
                "type": re.sub(r"\s+", "", str(field.get("type", ""))),
                "optional": bool(field.get("optional", False)),
            }
        else:
            normalised[str(name)] = {"value": " ".join(str(field.get("value", "")).split())}
    return {"record": normalised}


def describe_differences(expected: list, found: list) -> str:
    """Describe how the normalised records of ``meta.yml`` (``found``) differ from ``main.nf`` (``expected``)."""
    if len(expected) != 1 or len(found) != 1 or not isinstance(found[0], dict) or found[0].get("record") is None:
        return f"expected one `type: record` entry with `fields`, found {len(found)} entries"
    wanted, got = expected[0]["record"], found[0]["record"]
    parts = []
    if missing := [name for name in wanted if name not in got]:
        parts.append(f"missing field(s) `{'`, `'.join(missing)}`")
    if extra := [name for name in got if name not in wanted]:
        parts.append(f"field(s) not in `main.nf`: `{'`, `'.join(extra)}`")
    for name, attributes in wanted.items():
        for key, value in attributes.items():
            if name in got and got[name].get(key) != value:
                parts.append(f"`{name}` should have {key} `{value}`, found `{got[name].get(key)}`")
    return "; ".join(parts)
