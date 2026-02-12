"""Global pytest configuration for nf-core tests setting up worker-specific cache directories to avoid git lock issues."""

import contextlib
import os
import shutil
import sys
import tempfile
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
