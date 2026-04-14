#!/usr/bin/env python3
"""
Pre-commit hook: verify that every lint test name used in a result tuple is
mentioned in the docstring of its enclosing function.

Applies to nf-core component lint files where results are accumulated as:

    component.passed.append(("category", "test_name", "message", path))
    component.warned.append(("category", "test_name", "message", path))
    component.failed.append(("category", "test_name", "message", path))

Usage (called by pre-commit with the changed files as arguments):

    python scripts/check_lint_docstrings.py nf_core/modules/lint/module_tests.py ...
"""

import ast
import sys
from pathlib import Path


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
        test_names = collect_test_names(node)
        for test_name, lines in sorted(test_names.items()):
            if test_name not in docstring:
                errors.append(
                    f"{path}:{lines[0]}: '{test_name}' used in {node.name}() but not documented in its docstring"
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
