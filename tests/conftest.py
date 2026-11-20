"""Global pytest configuration for nf-core tests setting up worker-specific cache directories to avoid git lock issues."""

import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import warnings
from pathlib import Path
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _mock_interactive_session():
    """Mock TTY detection so tests behave as if running in an interactive session.

    Tests run in CI without a TTY, which causes is_interactive() to return False
    and auto-sets no_prompts=True. This fixture ensures consistent interactive
    behavior by default. Tests that specifically need non-interactive behavior
    can override with their own mock.
    """
    with (
        mock.patch.object(sys.stdin, "isatty", return_value=True),
        mock.patch.object(sys.stdout, "isatty", return_value=True),
        mock.patch.object(sys.stderr, "isatty", return_value=True),
    ):
        yield


def pytest_configure(config):
    """Configure pytest before any tests run - set up worker-specific cache directories."""
    # Get worker ID for pytest-xdist, or 'main' if not using xdist
    worker_id = getattr(config, "workerinput", {}).get("workerid", "main")

    # Create temporary directories for this worker
    cache_base = tempfile.mkdtemp(prefix=f"nfcore_cache_{worker_id}_")
    config_base = tempfile.mkdtemp(prefix=f"nfcore_config_{worker_id}_")

    # Store original values for later restoration
    config._original_xdg_cache = os.environ.get("XDG_CACHE_HOME")
    config._original_xdg_config = os.environ.get("XDG_CONFIG_HOME")
    config._temp_cache_dir = cache_base
    config._temp_config_dir = config_base

    # Set environment variables to use worker-specific directories
    os.environ["XDG_CACHE_HOME"] = cache_base
    os.environ["XDG_CONFIG_HOME"] = config_base

    _seed_modules_repo_clones(config, Path(config_base))


# Remotes cloned by the module/subworkflow tests, with the directory name ModulesRepo uses for them.
# Every worker has its own config directory (see pytest_configure), so without seeding each worker would
# clone them over the network; nf-core/modules alone is >200MB.
_SEEDED_REMOTES = {
    "https://github.com/nf-core/modules.git": "nf-core/modules",
    "https://gitlab.com/nf-core/modules-test.git": "nf-core/modules-test",
    "https://github.com/nf-core-test/modules.git": "nf-core-test/modules",
}


def _git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True, timeout=900)


def _seed_modules_repo_clones(config, config_base: Path) -> None:
    """
    Pre-populate this worker's modules repository cache with local clones of a shared bare mirror.

    The mirror is cloned once per machine (or ``NFCORE_TEST_GIT_MIRROR_DIR``) and fetched once per test run;
    worker clones are local, so they take a second instead of a full network clone. ModulesRepo then only
    fetches the latest changes from the real remote. Set ``NFCORE_TEST_NO_GIT_MIRROR=1`` to disable.
    """
    if os.environ.get("NFCORE_TEST_NO_GIT_MIRROR") or sys.platform == "win32":
        return
    import fcntl

    mirror_root = Path(
        os.environ.get("NFCORE_TEST_GIT_MIRROR_DIR") or Path(tempfile.gettempdir(), "nf-core-tests-git-mirrors")
    )
    # Workers of the same xdist run share a run id, so only the first one fetches
    run_id = getattr(config, "workerinput", {}).get("testrunuid") or uuid.uuid4().hex
    for remote, fullname in _SEEDED_REMOTES.items():
        mirror = mirror_root / f"{fullname.replace('/', '__')}.git"
        dest = config_base / "nfcore" / fullname
        try:
            mirror_root.mkdir(parents=True, exist_ok=True)
            with open(mirror_root / f"{mirror.name}.lock", "w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                stamp = mirror / "nf-core-tests-run-id"
                if not mirror.exists():
                    _git("clone", "--bare", "--quiet", remote, str(mirror))
                    _git("-C", str(mirror), "config", "remote.origin.fetch", "+refs/heads/*:refs/heads/*")
                elif not stamp.exists() or stamp.read_text() != run_id:
                    _git("-C", str(mirror), "fetch", "--quiet", "--prune", "origin")
                stamp.write_text(run_id)
                fcntl.flock(lock, fcntl.LOCK_UN)
                # Concurrent clones from the mirror are fine, only block while it is being updated
                fcntl.flock(lock, fcntl.LOCK_SH)
                _git("clone", "--quiet", str(mirror), str(dest))
                _git("-C", str(dest), "remote", "set-url", "origin", remote)
        except (OSError, subprocess.SubprocessError) as e:
            # Not fatal: ModulesRepo falls back to cloning from the remote
            warnings.warn(f"Could not seed a local clone of {remote}: {e}", stacklevel=1)
            shutil.rmtree(dest, ignore_errors=True)


def pytest_unconfigure(config):
    """Clean up after all tests are done."""
    # Restore original environment variables
    if hasattr(config, "_original_xdg_cache"):
        if config._original_xdg_cache is not None:
            os.environ["XDG_CACHE_HOME"] = config._original_xdg_cache
        else:
            os.environ.pop("XDG_CACHE_HOME", None)

    if hasattr(config, "_original_xdg_config"):
        if config._original_xdg_config is not None:
            os.environ["XDG_CONFIG_HOME"] = config._original_xdg_config
        else:
            os.environ.pop("XDG_CONFIG_HOME", None)

    # Clean up temporary directories
    if hasattr(config, "_temp_cache_dir"):
        with contextlib.suppress(OSError, FileNotFoundError):
            shutil.rmtree(config._temp_cache_dir)
    if hasattr(config, "_temp_config_dir"):
        with contextlib.suppress(OSError, FileNotFoundError):
            shutil.rmtree(config._temp_config_dir)
