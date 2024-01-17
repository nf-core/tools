"""Test covering the create-logo command."""

import tempfile
import unittest
from pathlib import Path

import nf_core.create_logo


class TestCreateLogo(unittest.TestCase):
    """Class for create-logo tests"""

    # create tempdir in setup step
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.tempdir_path = self.tempdir.name

    # delete tempdir in teardown step
    def tearDown(self):
        self.tempdir.cleanup()

    def test_create_logo_png(self):
        """Test that the create-logo command works for PNGs"""

        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("pipes", self.tempdir_path)
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that the file is a PNG
        self.assertTrue(logo_fn.suffix == ".png")
        # Check that the file is the right size
        fixture_fn = Path(__file__).parent / "fixtures" / "create_logo.png"
        self.assertTrue(logo_fn.stat().st_size == fixture_fn.stat().st_size)

    def test_create_logo_png_dark(self):
        """Test that the create-logo command works for dark PNGs"""

        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("pipes", self.tempdir_path, theme="dark")
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that the file is a PNG
        self.assertTrue(logo_fn.suffix == ".png")
        # Check that the file is the right size
        fixture_fn = Path(__file__).parent / "fixtures" / "create_logo_dark.png"
        self.assertTrue(logo_fn.stat().st_size == fixture_fn.stat().st_size)

    def test_create_log_png_width(self):
        """Test that the create-logo command works for PNGs with a custom width"""

        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("pipes", self.tempdir_path, width=100)
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that the file is a PNG
        self.assertTrue(logo_fn.suffix == ".png")
        # Check that the file is the right size
        fixture_fn = Path(__file__).parent / "fixtures" / "create_logo_width100.png"
        self.assertTrue(logo_fn.stat().st_size == fixture_fn.stat().st_size)
