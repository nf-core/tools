"""Tests covering the modules commands"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from git.repo import Repo

from .utils import GITLAB_NFTEST_BRANCH, GITLAB_URL


class TestComponents(unittest.TestCase):
    """Class for components tests"""

    def setUp(self):
        """Clone a testing version the nf-core/modules repo"""
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.nfcore_modules = Path(self.tmp_dir, "modules-test")

        Repo.clone_from(GITLAB_URL, self.nfcore_modules, branch=GITLAB_NFTEST_BRANCH)

        # Set $PROFILE environment variable to docker - tests will run with Docker
        if os.environ.get("PROFILE") is None:
            os.environ["PROFILE"] = "docker"

    def tearDown(self):
        """Clean up temporary files and folders"""

        # Clean up temporary files
        if self.tmp_dir.is_dir():
            shutil.rmtree(self.tmp_dir)

    ############################################
    # Test of the individual components commands. #
    ############################################

    from .components.generate_snapshot import (  # type: ignore[misc]
        test_generate_snapshot_module,
        test_generate_snapshot_once,
        test_generate_snapshot_subworkflow,
        test_test_not_found,
        test_unstable_snapshot,
        test_update_snapshot_module,
    )
    from .components.snapshot_test import (  # type: ignore[misc]
        test_components_test_check_inputs,
        test_components_test_no_installed_modules,
        test_components_test_no_name_no_prompts,
    )
