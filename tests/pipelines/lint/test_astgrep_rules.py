"""Generic harness for ast-grep lint rule tests.

Each rule in nf_core/pipelines/lint/rules/<id>.yml can ship a test file
tests/pipelines/lint/rules/<id>-test.yml in ast-grep's test-rule format
(https://ast-grep.github.io/guide/test-rule.html): `valid` snippets must not
match the rule, `invalid` snippets must. Adding a new rule needs no new
Python — just the rule file and a test file.
"""

from pathlib import Path

import pytest
import yaml

import nf_core.pipelines.lint
from nf_core import astgrep

RULES_DIR = Path(nf_core.pipelines.lint.__file__).parent / "rules"
TESTS_DIR = Path(__file__).parent / "rules"

pytestmark = pytest.mark.skipif(not astgrep.nextflow_available(), reason="tree-sitter-nextflow parser not available")


def rule_test_files():
    return sorted(TESTS_DIR.glob("*-test.yml"))


def test_every_rule_has_a_test_file():
    tested = {f.name.removesuffix("-test.yml") for f in rule_test_files()}
    rules = {f.stem for f in RULES_DIR.glob("*.yml")}
    assert rules == tested, f"rules without tests: {rules - tested}; tests without rules: {tested - rules}"


@pytest.mark.parametrize("test_file", rule_test_files(), ids=lambda p: p.name.removesuffix("-test.yml"))
def test_rule(test_file):
    with open(test_file) as fh:
        spec = yaml.safe_load(fh)
    rule_config = astgrep.load_rule(RULES_DIR / f"{spec['id']}.yml")

    snippets = [(s, True) for s in spec.get("valid", [])] + [(s, False) for s in spec.get("invalid", [])]
    for snippet, should_be_clean in snippets:
        # a snippet with an unquoted `foo: bar` parses as a YAML map, not a string
        assert isinstance(snippet, str), f"snippet in {test_file.name} is not a string (quote it?): {snippet!r}"
        matches = astgrep.scan(snippet, rule_config)
        if should_be_clean:
            assert not matches, f"valid snippet matched {spec['id']}: {snippet!r}"
        else:
            assert matches, f"invalid snippet did not match {spec['id']}: {snippet!r}"
