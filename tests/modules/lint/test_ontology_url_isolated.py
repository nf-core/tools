"""Distinguish actual ontology URLs from unrelated malformed scalar values."""

import pytest
from jsonschema.exceptions import ValidationError

from nf_core.modules.lint.meta_yml import _has_bare_ontology_url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("http://edamontology.org/format_1975", True),
        ("https://edamontology.org/format_1975", True),
        ("just-a-string", False),
        ("http://", False),
        ("ftp://edamontology.org/format_1975", False),
        ("not a URL", False),
    ],
)
def test_bare_url_diagnostic_only_for_http_urls(value, expected):
    leaf = ValidationError(
        "is not of type object",
        validator="type",
        validator_value="object",
        instance=value,
        path=["ontologies", 0],
    )
    parent = ValidationError("failed oneOf", validator="oneOf", context=[leaf])
    assert _has_bare_ontology_url(parent) is expected


def test_unrelated_object_type_errors_do_not_claim_ontology_urls():
    unrelated = ValidationError(
        "is not of type object",
        validator="type",
        validator_value="object",
        instance="https://example.com/",
        path=["description"],
    )
    assert not _has_bare_ontology_url(unrelated)
