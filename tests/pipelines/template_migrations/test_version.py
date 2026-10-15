"""Tests for reading and stamping nf_core_version"""

from nf_core.pipelines.template_migrations.version import parse_version, stamp_version


def test_parse_version_reads_a_quoted_version() -> None:
    # Given / When
    version = parse_version('repository_type: pipeline\nnf_core_version: "3.5.2"\n')

    # Then
    assert version == "3.5.2"


def test_parse_version_without_a_version_line_is_none() -> None:
    # Given / When
    version = parse_version("repository_type: pipeline\n")

    # Then
    assert version is None


def test_stamp_version_keeps_comments() -> None:
    # Given
    nf_core_yml = "# Held below the synced version\nnf_core_version: 4.0.3\nrepository_type: pipeline\n"

    # When
    stamped = stamp_version(nf_core_yml, "4.1.0")

    # Then
    assert stamped == "# Held below the synced version\nnf_core_version: 4.1.0\nrepository_type: pipeline\n"


def test_stamp_version_adds_a_missing_version_line() -> None:
    # Given / When
    stamped = stamp_version("repository_type: pipeline\n", "4.1.0")

    # Then
    assert stamped == "nf_core_version: 4.1.0\nrepository_type: pipeline\n"
