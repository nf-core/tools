"""Structural (AST-based) matching of Nextflow code via ast-grep.

Uses the tree-sitter-nextflow grammar (https://github.com/nextflow-io/tree-sitter-nextflow)
registered as an ast-grep custom language. The compiled parser library is discovered from:

1. The ``NFCORE_TREE_SITTER_NEXTFLOW_LIB`` environment variable (path to
   ``libnextflow.so`` / ``libnextflow.dylib``),
2. An installed ``tree-sitter-nextflow`` Python package (its compiled binding
   exports the ``tree_sitter_nextflow`` symbol ast-grep needs); until it is on
   PyPI, install with
   ``pip install git+https://github.com/nextflow-io/tree-sitter-nextflow.git``, or
3. A global ast-grep install (``~/.config/ast-grep/sgconfig.yml``), as set up by
   tree-sitter-nextflow's ``install-ast-grep.sh --global``.

If none is available, :func:`nextflow_available` returns ``False`` and callers
should fall back to text-based matching.
"""

import logging
import os
import platform
import re
import sys
from collections.abc import Iterable
from functools import cache
from pathlib import Path

import yaml

log = logging.getLogger(__name__)

#: File extensions that the Nextflow grammar can parse (error recovery makes
#: it usable for plain Groovy lib files too)
NEXTFLOW_EXTENSIONS = {".nf", ".config", ".groovy"}

GLOBAL_SGCONFIG = Path.home() / ".config" / "ast-grep" / "sgconfig.yml"


def _platform_triple() -> str | None:
    """Rust-style target triple used as libraryPath key in sgconfig.yml."""
    arch = {"arm64": "aarch64", "aarch64": "aarch64", "x86_64": "x86_64", "amd64": "x86_64"}.get(
        platform.machine().lower()
    )
    os_part = {"darwin": "apple-darwin", "linux": "unknown-linux-gnu", "win32": "pc-windows-msvc"}.get(sys.platform)
    if arch and os_part:
        return f"{arch}-{os_part}"
    return None


def _find_library() -> Path | None:
    """Locate the compiled tree-sitter-nextflow parser library."""
    env_path = os.environ.get("NFCORE_TREE_SITTER_NEXTFLOW_LIB")
    if env_path:
        if Path(env_path).is_file():
            return Path(env_path)
        log.debug(f"NFCORE_TREE_SITTER_NEXTFLOW_LIB set but not a file: {env_path}")

    try:
        import tree_sitter_nextflow

        lib = next(Path(tree_sitter_nextflow.__file__).parent.glob("_binding*"), None)
        if lib is not None:
            return lib
    except ImportError:
        pass

    if GLOBAL_SGCONFIG.is_file():
        try:
            with open(GLOBAL_SGCONFIG) as fh:
                config = yaml.safe_load(fh)
            library_path = config["customLanguages"]["nextflow"]["libraryPath"]
            if isinstance(library_path, dict):
                library_path = library_path.get(_platform_triple())
            if library_path:
                lib = GLOBAL_SGCONFIG.parent / library_path
                if lib.is_file():
                    return lib
        except (KeyError, TypeError, yaml.YAMLError) as e:
            log.debug(f"Could not read nextflow language from {GLOBAL_SGCONFIG}: {e}")

    return None


@cache
def nextflow_available() -> bool:
    """Register the Nextflow custom language with ast-grep (once per process).

    Returns False if ast-grep-py or the compiled parser library is unavailable.
    """
    try:
        from ast_grep_py import register_dynamic_language
    except ImportError:
        log.debug("ast-grep-py not installed, structural Nextflow linting unavailable")
        return False

    lib = _find_library()
    if lib is None:
        log.debug("tree-sitter-nextflow parser library not found, structural Nextflow linting unavailable")
        return False

    try:
        register_dynamic_language(
            {
                "nextflow": {
                    "library_path": str(lib),
                    "language_symbol": "tree_sitter_nextflow",
                    "expando_char": "_",
                    # required at runtime but missing from the CustomLang type stub
                    "extensions": ["nf", "config"],  # type: ignore[typeddict-unknown-key]
                }
            }
        )
    except RuntimeError as e:
        # e.g. an outdated library that does not export the parser symbol
        log.debug(f"Could not register Nextflow ast-grep language from {lib}: {e}")
        return False
    log.debug(f"Registered Nextflow ast-grep language from {lib}")
    return True


def find_all(source: str, rule: dict):
    """Find all nodes in Nextflow source matching an ast-grep rule.

    Callers must check :func:`nextflow_available` first.
    """
    from ast_grep_py import SgRoot

    return SgRoot(source, "nextflow").root().find_all(**rule)


@cache
def load_rule(path: Path) -> dict:
    """Load an ast-grep lint rule file (id, severity, message, rule, ...)."""
    with open(path) as fh:
        return yaml.safe_load(fh)


def scan(source: str, rule_config: dict):
    """Find all nodes matching a full ast-grep rule config (rule/constraints/utils)."""
    from ast_grep_py import SgRoot

    config = {key: rule_config[key] for key in ("rule", "constraints", "utils") if key in rule_config}
    return SgRoot(source, "nextflow").root().find_all(config=config)


def find_matches(rule_config: dict, files: Iterable[Path | str], regex_unparseable: bool = False):
    """Yield ``(file, line_number, snippet)`` for every rule match across files.

    A Nextflow/Groovy file is matched structurally only when the parser is
    available AND the file parses without ERROR nodes. A broken parse can
    swallow the rest of a file (e.g. process directives the grammar does not
    know yet), so any parse error means that file falls back to line-by-line
    matching with the rule's ``metadata.fallback-regex`` — recall never drops
    below regex level, and precision upgrades as the grammar matures.

    ``regex_unparseable`` controls files the Nextflow grammar cannot parse at
    all (e.g. markdown, yaml) when the parser is available: skipped by
    default, regex-scanned if True (for rules that target all file types,
    like TODOs).
    """
    structural = nextflow_available()
    pattern = re.compile(rule_config["metadata"]["fallback-regex"])
    for file in map(Path, files):
        try:
            text = file.read_text(encoding="latin1")
        except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
            log.debug(f"Could not open file {file} while scanning for {rule_config.get('id')}: {e}")
            continue

        if structural and file.suffix in NEXTFLOW_EXTENSIONS:
            from ast_grep_py import SgRoot

            root = SgRoot(text, "nextflow").root()
            if root.find(kind="ERROR") is None:
                config = {key: rule_config[key] for key in ("rule", "constraints", "utils") if key in rule_config}
                for match in root.find_all(config=config):
                    yield file, match.range().start.line + 1, match.text()
                continue
            log.debug(f"{file} has parse errors, falling back to regex for {rule_config.get('id')}")
        elif structural and not regex_unparseable:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                yield file, line_number, line.strip()
