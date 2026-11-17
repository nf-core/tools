"""
Parse the ``record(...)`` declarations of modules that use Nextflow static types
(``nextflow.enable.types = true``).
"""

import re
from typing import Any

TYPED_MODULE_RE = re.compile(r"^\s*nextflow\.enable\.types\s*=\s*true\b", re.MULTILINE)
SECTION_RE = re.compile(r"^\s*(input|output|topic|when|script|shell|exec|stub)\s*:\s*$")
TOPIC_TARGET_RE = re.compile(r"^\s*>>\s*(['\"])(\w+)\1")

_OPENERS = {"(": ")", "[": "]", "{": "}"}
_CLOSERS = set(_OPENERS.values())


def is_typed(main_nf: str) -> bool:
    """Whether a module enables static types."""
    return TYPED_MODULE_RE.search(main_nf) is not None


def is_record(entry: Any) -> bool:
    """Whether a ``meta.yml`` input, output or topic entry uses the record layout."""
    return isinstance(entry, dict) and entry.get("type") == "record"


def _scan(text: str, angle_brackets: bool = False):
    """Yield ``(index, char, depth)`` for every character outside string literals.

    ``depth`` is the bracket nesting level before the character. ``<``/``>`` only
    nest when ``angle_brackets`` is set, because they are operators outside type annotations.
    """
    depth = 0
    quote = None
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == quote:
                quote = None
        elif char in ("'", '"'):
            quote = char
        else:
            yield i, char, depth
            if char in _OPENERS or (angle_brackets and char == "<"):
                depth += 1
            elif char in _CLOSERS or (angle_brackets and char == ">"):
                depth -= 1
        i += 1


def strip_comments(text: str) -> str:
    """Remove ``//`` line comments, leaving ``//`` inside string literals intact."""
    lines = []
    for line in text.split("\n"):
        previous = -1
        for i, char, _ in _scan(line):
            if char == "/":
                if previous == i - 1:
                    line = line[: i - 1]
                    break
                previous = i
        lines.append(line)
    return "\n".join(lines)


def split_sections(lines: list[str]) -> dict[str, str]:
    """Return the text of each ``<label>:`` section of a process, keyed by label."""
    sections: dict[str, list[str]] = {}
    current = None
    for line in lines:
        match = SECTION_RE.match(line)
        if match:
            current = match.group(1)
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line.rstrip("\n"))
    return {name: "\n".join(body) for name, body in sections.items()}


def split_top_level(text: str, angle_brackets: bool = False) -> list[str]:
    """Split ``text`` on commas that are outside brackets and string literals."""
    parts = []
    start = 0
    for i, char, depth in _scan(text, angle_brackets):
        if char == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


def find_records(text: str) -> list[tuple[str, str]]:
    """Find each top-level ``record(...)`` call in ``text``.

    Returns:
        A list of ``(arguments, trailing)`` pairs, where ``trailing`` is the text
        after the closing parenthesis up to the next record (e.g. ``>> 'versions'``).
    """
    text = strip_comments(text)
    spans = []
    open_at = None
    for i, char, depth in _scan(text):
        if char == "(" and depth == 0 and re.search(r"(?<![\w.])record\s*$", text[:i]):
            open_at = i
        elif char == ")" and depth == 1 and open_at is not None:
            spans.append((open_at, i))
            open_at = None
    records = []
    for n, (start, end) in enumerate(spans):
        next_start = spans[n + 1][0] if n + 1 < len(spans) else len(text)
        records.append((text[start + 1 : end], text[end + 1 : next_start]))
    return records


def parse_record_fields(arguments: str, angle_brackets: bool = False) -> dict[str, str]:
    """Parse ``name: expression`` pairs from the arguments of a ``record(...)`` call."""
    fields = {}
    for part in split_top_level(arguments, angle_brackets):
        name, sep, expression = part.partition(":")
        if sep and re.fullmatch(r"\s*\w+\s*", name):
            fields[name.strip()] = " ".join(expression.split())
    return fields


def parse_type(annotation: str) -> tuple[str, bool]:
    """Split a type annotation such as ``Record?`` into its type and whether it is optional."""
    annotation = re.sub(r"\s+", "", annotation)
    optional = annotation.endswith("?")
    return annotation.removesuffix("?"), optional


def input_record(arguments: str) -> dict:
    """Describe an input ``record(...)`` declaration in the ``meta.yml`` record layout."""
    fields = {}
    for name, annotation in parse_record_fields(arguments, angle_brackets=True).items():
        type_, optional = parse_type(annotation)
        fields[name] = {"type": type_, "optional": optional}
    return {"type": "record", "fields": fields}


def value_record(arguments: str) -> dict:
    """Describe an output or topic ``record(...)`` declaration in the ``meta.yml`` record layout."""
    return {
        "type": "record",
        "fields": {name: {"value": value} for name, value in parse_record_fields(arguments).items()},
    }


def topic_records(text: str) -> dict[str, list[dict]]:
    """Group the ``record(...) >> 'topic'`` statements of a ``topic:`` section by topic name."""
    topics: dict[str, list[dict]] = {}
    for arguments, trailing in find_records(text):
        match = TOPIC_TARGET_RE.match(trailing)
        if match:
            topics.setdefault(match.group(2), []).append(value_record(arguments))
    return topics


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
