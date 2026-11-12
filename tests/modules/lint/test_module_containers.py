import logging
from pathlib import Path
from unittest import mock

from nf_core.modules.lint.module_containers import lint_main_nf_container, lint_meta_yml_containers


def _make_component(component_dir: Path, *, has_dockerfile: bool = False, has_env_yml: bool = False):
    """Return a mock NFCoreComponent with a real filesystem layout."""
    if has_dockerfile:
        (component_dir / "Dockerfile").write_text("FROM ubuntu:22.04\n")
    env_yml_path = component_dir / "environment.yml"
    if has_env_yml:
        env_yml_path.write_text("name: test\n")

    comp = mock.Mock()
    comp.component_dir = component_dir
    comp.component_name = "test/module"
    comp.environment_yml = env_yml_path if has_env_yml else None
    comp.passed = []
    comp.warned = []
    comp.failed = []
    return comp


# ---------------------------------------------------------------------------
# lint_meta_yml_containers – Dockerfile skip
# ---------------------------------------------------------------------------


def test_lint_meta_yml_containers_skips_dockerfile_module(tmp_path, caplog):
    comp = _make_component(tmp_path, has_dockerfile=True)
    with caplog.at_level(logging.DEBUG, logger="nf_core.modules.lint.module_containers"):
        lint_meta_yml_containers(comp)
    assert comp.passed == []
    assert comp.warned == []
    assert comp.failed == []
    assert "Dockerfile" in caplog.text


def test_lint_meta_yml_containers_skips_all_skip_flags_ignored_for_dockerfile(tmp_path):
    """All skip flags should be irrelevant; the Dockerfile path returns unconditionally."""
    comp = _make_component(tmp_path, has_dockerfile=True)
    lint_meta_yml_containers(comp, skip_docker=True, skip_conda=True, skip_singularity=True)
    assert comp.passed == []
    assert comp.warned == []
    assert comp.failed == []


# ---------------------------------------------------------------------------
# lint_main_nf_container – Dockerfile skip
# ---------------------------------------------------------------------------


def test_lint_main_nf_container_skips_dockerfile_module(tmp_path, caplog):
    comp = _make_component(tmp_path, has_dockerfile=True)
    with caplog.at_level(logging.DEBUG, logger="nf_core.modules.lint.module_containers"):
        lint_main_nf_container(comp)
    assert comp.passed == []
    assert comp.warned == []
    assert comp.failed == []
    assert "Dockerfile" in caplog.text


def test_lint_main_nf_container_dockerfile_skip_flag_ignored(tmp_path):
    """skip_docker=True is a separate code path; Dockerfile modules return even earlier."""
    comp = _make_component(tmp_path, has_dockerfile=True)
    lint_main_nf_container(comp, skip_docker=True)
    assert comp.passed == []
    assert comp.warned == []
    assert comp.failed == []
