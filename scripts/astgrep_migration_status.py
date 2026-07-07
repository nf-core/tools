#!/usr/bin/env python3
"""Report how many nf-core lint checks use ast-grep YAML rules vs Python/regex.

A check counts as migrated if its own module uses `nf_core.astgrep`, or if it
delegates (via `from nf_core.<area>.lint.<name> import ...`) to a module that does.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AREAS = {
    "pipelines": ROOT / "nf_core" / "pipelines" / "lint",
    "modules": ROOT / "nf_core" / "modules" / "lint",
    "subworkflows": ROOT / "nf_core" / "subworkflows" / "lint",
}
RULES_DIR = ROOT / "nf_core" / "pipelines" / "lint" / "rules"
IMPORT_RE = re.compile(r"from nf_core\.\w+\.lint\.(\w+) import")


def is_check(path: Path) -> bool:
    stem = path.stem
    return path.suffix == ".py" and stem != "__init__" and stem != "lint_utils" and not stem.startswith("_")


def scan() -> tuple[dict[str, bool], dict[str, set[str]]]:
    """Return (direct: stem->astgrep in own source, imports: stem->imported lint stems)."""
    direct: dict[str, bool] = {}
    imports: dict[str, set[str]] = {}
    for area_dir in AREAS.values():
        for path in area_dir.glob("*.py"):
            if not is_check(path):
                continue
            text = path.read_text()
            direct[path.stem] = "astgrep" in text
            imports[path.stem] = set(IMPORT_RE.findall(text))
    return direct, imports


def is_migrated(stem: str, direct: dict[str, bool], imports: dict[str, set[str]], seen: set[str] | None = None) -> bool:
    seen = seen if seen is not None else set()
    if stem in seen:
        return False
    seen.add(stem)
    if direct.get(stem):
        return True
    return any(is_migrated(dep, direct, imports, seen) for dep in imports.get(stem, ()))


def build() -> dict:
    direct, imports = scan()
    result: dict = {}
    for area, area_dir in AREAS.items():
        checks = sorted(p.stem for p in area_dir.glob("*.py") if is_check(p))
        migrated = [c for c in checks if is_migrated(c, direct, imports)]
        result[area] = {
            "total": len(checks),
            "migrated": migrated,
            "not_migrated": [c for c in checks if c not in migrated],
        }
    result["rules"] = sorted(p.name for p in RULES_DIR.glob("*.yml")) if RULES_DIR.is_dir() else []
    return result


def print_table(data: dict) -> None:
    total = migrated = 0
    for area in AREAS:
        d = data[area]
        total += d["total"]
        migrated += len(d["migrated"])
        print(f"\n{area}: {len(d['migrated'])}/{d['total']} migrated")
        print(f"  migrated:     {', '.join(d['migrated']) or '-'}")
        print(f"  not migrated: {', '.join(d['not_migrated']) or '-'}")
    pct = round(100 * migrated / total) if total else 0
    print(f"\n{migrated}/{total} lint modules use ast-grep rules ({pct}%)")
    print(f"\nrule files in nf_core/pipelines/lint/rules/ ({len(data['rules'])}):")
    for name in data["rules"]:
        print(f"  {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()
    data = build()
    if args.json:
        json.dump(data, sys.stdout, indent=2)
        print()
    else:
        print_table(data)


if __name__ == "__main__":
    main()
