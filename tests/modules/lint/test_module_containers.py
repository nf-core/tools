import contextlib
import logging
from pathlib import Path
from unittest import mock

import pytest

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


# ---------------------------------------------------------------------------
# lint_meta_yml_containers – conda lock_file resolved against repo root
# ---------------------------------------------------------------------------

LOCK_FILE = "modules/nf-core/test/module/.conda-lock/linux_amd64-bd-abc123_1.txt"


@pytest.mark.parametrize("write_lock", [True, False], ids=["found_from_other_cwd", "missing_warns"])
def test_lint_conda_lock_file_resolved_from_repo_root(tmp_path, write_lock):
    repo = tmp_path / "repo"
    lock = repo / LOCK_FILE
    lock.parent.mkdir(parents=True)
    if write_lock:
        lock.write_text("# lock\n")

    comp = _make_component(lock.parent.parent)
    comp.base_dir = repo
    comp.load_meta_yml.return_value = {"containers": {"conda": {"linux/amd64": {"lock_file": LOCK_FILE}}}}

    # cwd outside the repo, so a cwd-relative lookup would miss the lock file
    with contextlib.chdir(tmp_path):
        lint_meta_yml_containers(comp, skip_docker=True, skip_singularity=True)

    def lock_checks(results):
        return [r for r in results if r[1] == "containers_conda_lock_exists"]

    assert (len(lock_checks(comp.passed)), len(lock_checks(comp.warned))) == ((1, 0) if write_lock else (0, 1))
