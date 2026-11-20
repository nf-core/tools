#!/usr/bin/env python3
"""
Pre-commit hook: keep each module's ``__lazy_modules__`` list in sync with its imports.

``__lazy_modules__`` is the backwards-compatible form of PEP 810 explicit lazy
imports. On Python 3.15+ every top-level import of a module named in the list is
deferred until the imported name is first used; older Python versions ignore the
list and import eagerly as usual. This trims CLI start-up time on 3.15+ without
the ``lazy import`` syntax, which would be a SyntaxError on Python < 3.15.

The list holds every non-stdlib module imported at the top level of the file.
Imports nested in ``try``, ``if``, functions or classes are skipped: they are
either never lazy (``try``) or already deferred. Standard-library modules are
skipped because they are cheap or already loaded by the time nf-core runs.

Usage (called by pre-commit with the changed files as arguments):

    python scripts/update_lazy_modules.py nf_core/utils.py ...

Exits 1 if any file was changed, so pre-commit reports the fix.
"""

import ast
import sys
from pathlib import Path

MARKER = "__lazy_modules__"
COMMENT = "# Lazy on Python 3.15+ (PEP 810), see scripts/update_lazy_modules.py\n"
LINE_LENGTH = 120


def module_name(path: Path) -> tuple[str, bool]:
    """Dotted module name for ``path`` and whether it is a package ``__init__``."""
    parts = list(path.resolve().with_suffix("").parts)
    parts = parts[len(parts) - 1 - parts[::-1].index("nf_core") :]
    is_package = parts[-1] == "__init__"
    if is_package:
        parts.pop()
    return ".".join(parts), is_package


def lazy_targets(tree: ast.Module, path: Path) -> list[str]:
    """Absolute names of the non-stdlib modules imported at the top level of ``tree``."""
    name, is_package = module_name(path)
    package = name if is_package else name.rpartition(".")[0]
    targets: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != "__future__":
            if node.level:
                base = package.split(".")[: len(package.split(".")) - node.level + 1]
                if node.module:
                    base.append(node.module)
                else:
                    # `from . import x` may import submodule `x`
                    targets.update(".".join([*base, alias.name]) for alias in node.names)
                targets.add(".".join(base))
            elif node.module:
                targets.add(node.module)
    return sorted(t for t in targets if t and t.split(".")[0] not in sys.stdlib_module_names)


def render(targets: list[str]) -> str:
    quoted = [f'"{t}"' for t in targets]
    one_line = f"{MARKER} = [{', '.join(quoted)}]"
    if len(one_line) <= LINE_LENGTH:
        return f"{COMMENT}{one_line}\n"
    items = "".join(f"    {q},\n" for q in quoted)
    return f"{COMMENT}{MARKER} = [\n{items}]\n"


def update(path: Path) -> bool:
    source = path.read_text()
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    targets = lazy_targets(tree, path)

    existing = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == MARKER for t in node.targets)
        ),
        None,
    )
    if existing:
        start, end = existing.lineno - 1, existing.end_lineno or existing.lineno
        if start and lines[start - 1] == COMMENT:
            start -= 1
        if not targets:
            # Drop the block and the blank line that follows it
            if end < len(lines) and not lines[end].strip():
                end += 1
            del lines[start:end]
        else:
            lines[start:end] = [render(targets)]
    elif targets:
        first_import = next(
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom)) and getattr(node, "module", None) != "__future__"
        )
        at = first_import.lineno - 1
        # Keep comments that sit directly above the first import attached to it
        while at and lines[at - 1].lstrip().startswith("#"):
            at -= 1
        block = render(targets) + "\n"
        if at and lines[at - 1].strip():
            block = "\n" + block
        lines.insert(at, block)

    new_source = "".join(lines)
    if new_source == source:
        return False
    path.write_text(new_source)
    print(f"Updated {MARKER} in {path}")
    return True


if __name__ == "__main__":
    changed = [update(Path(arg)) for arg in sys.argv[1:]]
    sys.exit(1 if any(changed) else 0)
