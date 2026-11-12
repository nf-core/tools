#!/usr/bin/env python3
"""
Pre-commit hook: verify that every lint test name used in a result tuple is
documented as a section heading in the docstring of its enclosing function.

Applies to nf-core component lint files where results are accumulated as:

    component.passed.append(("category", "test_name", "message", path))
    component.warned.append(("category", "test_name", "message", path))
    component.failed.append(("category", "test_name", "message", path))

The heading requirement (rather than a plain substring match) exists because
the linter links each result to ``.../<parent_lint_test>#<test_name>``. That
anchor only resolves on the docs site if ``test_name`` is rendered as a
heading, i.e. the docstring must contain an RST section of the form::

    test_name
    ^^^^^^^^^

Usage (called by pre-commit with the changed files as arguments):

    python scripts/check_lint_docstrings.py nf_core/modules/lint/module_tests.py ...
"""

import ast
import sys
from pathlib import Path

# Punctuation characters reStructuredText accepts as section-title adornments.
_RST_ADORNMENTS = set("=-`:.'\"~^_*+#<>!$%&(),/;?@[\\]{|}")


def collect_doc_headings(docstring: str) -> set[str]:
    """Return the set of RST section-heading titles found in a docstring.

    A heading is a non-empty title line immediately followed by an underline
    line built from a single, repeated adornment character that is at least as
    long as the title (matching reStructuredText section syntax). ``docstring``
    is assumed to be dedented (as returned by ``ast.get_docstring``).
    """
    headings: set[str] = set()
    lines = docstring.splitlines()
    for title_line, underline_line in zip(lines, lines[1:], strict=False):
        title = title_line.strip()
        underline = underline_line.strip()
        if (
            title
            and underline
            and len(underline) >= len(title)
            and len(set(underline)) == 1
            and underline[0] in _RST_ADORNMENTS
        ):
            headings.add(title)
    return headings


def collect_test_names(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, list[int]]:
    """Return {test_name: [line_numbers]} for all result-tuple appends in the function."""
    results: dict[str, list[int]] = {}
    # Walk only the direct body — do not descend into nested function definitions.
    nodes_to_visit: list[ast.AST] = list(func_node.body)
    while nodes_to_visit:
        node = nodes_to_visit.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # skip nested scopes
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr in ("passed", "warned", "failed")
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Tuple)
            and len(node.args[0].elts) >= 2
            and isinstance(node.args[0].elts[1], ast.Constant)
            and isinstance(node.args[0].elts[1].value, str)
        ):
            test_name = node.args[0].elts[1].value
            results.setdefault(test_name, []).append(node.lineno)
        nodes_to_visit.extend(ast.iter_child_nodes(node))
    return results


def check_file(path: Path) -> list[str]:
    errors = []
    try:
        source = path.read_text()
    except OSError as e:
        return [f"{path}: could not read file: {e}"]

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        return [f"{path}: SyntaxError: {e}"]

    module_stem = path.stem  # e.g. "module_tests" from "module_tests.py"

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != module_stem:
            continue
        docstring = ast.get_docstring(node) or ""
        headings = collect_doc_headings(docstring)
        test_names = collect_test_names(node)
        for test_name, lines in sorted(test_names.items()):
            if test_name not in headings:
                errors.append(
                    f"{path}:{lines[0]}: '{test_name}' is emitted by {node.name}() but is not "
                    f"documented as a section heading in its docstring (required for the docs "
                    f"anchor #{test_name})"
                )
        break  # only one function per file can match the stem
    return errors


def main() -> int:
    files = [Path(f) for f in sys.argv[1:] if f.endswith(".py")]
    all_errors: list[str] = []
    for path in files:
        all_errors.extend(check_file(path))
    for error in all_errors:
        print(error, file=sys.stderr)
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
