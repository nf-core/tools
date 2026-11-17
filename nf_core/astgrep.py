"""Structural (AST-based) matching of Nextflow code via ast-grep.

Uses the tree-sitter-nextflow grammar (https://github.com/nextflow-io/tree-sitter-nextflow)
registered as an ast-grep custom language. The compiled parser library is discovered from:

1. The ``NFCORE_TREE_SITTER_NEXTFLOW_LIB`` environment variable (path to
   ``libnextflow.so`` / ``libnextflow.dylib``),
2. The installed ``tree-sitter-nextflow`` package (its compiled binding
   exports the ``tree_sitter_nextflow`` symbol ast-grep needs), or
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
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from ast_grep_py import SgNode
    from tree_sitter import Parser

log = logging.getLogger(__name__)

#: File extensions handed to the Nextflow grammar. Groovy files with class
#: definitions usually fail to parse and fall back to regex matching.
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


@cache
def _error_checker() -> "Parser | None":
    """py-tree-sitter parser, used only for ``has_error`` (ast-grep-py cannot see MISSING nodes)."""
    try:
        import tree_sitter_nextflow
        from tree_sitter import Language, Parser
    except ImportError:
        return None
    return Parser(Language(tree_sitter_nextflow.language()))


def has_parse_errors(source: str, root: "SgNode | None" = None) -> bool:
    """True if ``source`` does not parse cleanly (ERROR *or* MISSING nodes).

    Falls back to an ERROR-node search on ``root`` if py-tree-sitter is not installed.
    """
    parser = _error_checker()
    if parser is not None:
        return parser.parse(source.encode("utf-8")).root_node.has_error
    if root is None:
        from ast_grep_py import SgRoot

        root = SgRoot(source, "nextflow").root()
    return root.find(kind="ERROR") is not None


@cache
def load_rule(path: Path) -> dict:
    """Load and validate an ast-grep lint rule file (id, severity, message, rule, ...)."""
    with open(path) as fh:
        rule = yaml.safe_load(fh)
    missing = {"id", "language", "message", "rule"} - set(rule or {})
    if missing:
        raise ValueError(f"ast-grep rule {path} is missing required keys: {', '.join(sorted(missing))}")
    if rule["language"] != "nextflow":
        raise ValueError(f"ast-grep rule {path} must set `language: nextflow`, not {rule['language']!r}")
    return rule


#: Keys of a rule file that ast-grep's ``find_all(config=...)`` understands
_RULE_CONFIG_KEYS = ("rule", "constraints", "utils")


def _rule_config(rule_config: dict) -> dict:
    return {key: rule_config[key] for key in _RULE_CONFIG_KEYS if key in rule_config}


def scan(source: str, rule_config: dict):
    """Find all nodes matching a full ast-grep rule config (rule/constraints/utils)."""
    from ast_grep_py import SgRoot

    return SgRoot(source, "nextflow").root().find_all(config=_rule_config(rule_config))


#: Rule ids that failed to compile against the installed grammar (warned once, then regex only)
_INVALID_RULES: set[str] = set()


def find_matches(rule_config: dict, files: Iterable[Path | str], regex_unparseable: bool = False):
    """Yield ``(file, line_number, snippet)`` for every rule match across files.

    A Nextflow/Groovy file is matched structurally only when the parser is
    available AND the file parses cleanly (no ERROR or MISSING nodes). A broken
    parse can swallow the rest of a file, so any parse error means that file
    falls back to line-by-line matching with the rule's optional
    ``metadata.fallback-regex`` — recall never drops below regex level, and
    precision upgrades as the grammar matures. A rule that fails to compile
    against the installed grammar (e.g. an unknown node kind) logs one warning
    and uses its regex from then on.

    Files with other extensions (e.g. markdown, yaml) are skipped unless
    ``regex_unparseable`` is True (for rules that target all file types, like
    TODOs); this is the same whether or not the parser is installed.
    """
    structural = nextflow_available()
    rule_id = str(rule_config.get("id"))
    fallback = (rule_config.get("metadata") or {}).get("fallback-regex")
    pattern = re.compile(fallback) if fallback else None
    for file in map(Path, files):
        try:
            text = file.read_text(encoding="utf-8", errors="replace")
        except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
            log.debug(f"Could not open file {file} while scanning for {rule_id}: {e}")
            continue

        is_nextflow = file.suffix in NEXTFLOW_EXTENSIONS
        if structural and is_nextflow and rule_id not in _INVALID_RULES:
            from ast_grep_py import SgRoot

            root = SgRoot(text, "nextflow").root()
            if not has_parse_errors(text, root):
                try:
                    matches = root.find_all(config=_rule_config(rule_config))
                except RuntimeError as e:
                    # e.g. the rule uses a node kind the installed grammar does not have
                    _INVALID_RULES.add(rule_id)
                    reason = str(e).splitlines()[0]
                    log.warning(f"ast-grep rule {rule_id!r} is invalid for this grammar ({reason}), using regex")
                else:
                    for match in matches:
                        yield file, match.range().start.line + 1, match.text()
                    continue
            else:
                log.debug(f"{file} has parse errors, falling back to regex for {rule_id}")
        elif not is_nextflow and not regex_unparseable:
            continue

        if pattern is None:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                yield file, line_number, line.strip()
