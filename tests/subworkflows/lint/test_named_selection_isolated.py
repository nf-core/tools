"""Verify named local and remote selection without a Nextflow fixture."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from nf_core.components.lint import LintExceptionError
from nf_core.subworkflows.lint import SubworkflowLint


def selection():
    wanted_local = SimpleNamespace(component_name="target")
    wanted_remote = SimpleNamespace(component_name="target")
    other_local = SimpleNamespace(component_name="other")
    obj = SimpleNamespace(
        all_local_components=[wanted_local, other_local],
        all_remote_components=[wanted_remote],
        repo_type="modules",
        directory="/tmp",
        lint_subworkflows=Mock(),
    )
    return obj, wanted_local, wanted_remote


@pytest.mark.parametrize("local", [True, False])
def test_explicit_component_uses_correct_index(local):
    obj, wanted_local, wanted_remote = selection()
    SubworkflowLint.lint(obj, subworkflow="target", local=local, print_results=False)
    obj.lint_subworkflows.assert_called_once_with([wanted_local if local else wanted_remote], local=local)


def test_unknown_named_local_component_still_raises():
    obj, _, _ = selection()
    with pytest.raises(LintExceptionError, match="Could not find the specified subworkflow"):
        SubworkflowLint.lint(obj, subworkflow="missing", local=True, print_results=False)
    obj.lint_subworkflows.assert_not_called()


def test_named_component_rejects_all_components_flag():
    obj, _, _ = selection()
    with pytest.raises(LintExceptionError, match="You cannot specify"):
        SubworkflowLint.lint(obj, subworkflow="target", all_subworkflows=True, local=True, print_results=False)
