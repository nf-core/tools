"""Test covering the create-logo command."""

import tempfile
import unittest
from shutil import copyfile

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
        logo_fn = nf_core.create_logo.Logo().create("pipes", self.tempdir_path, format="png")
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that the file is a PNG
        self.assertTrue(logo_fn.suffix == ".png")
        # Check that the file is the right size
        self.assertTrue(logo_fn.stat().st_size > 57000)
        print(logo_fn.stat().st_size)

    def test_create_logo_default(self):
        """Test that the create-logo command works for SVGs"""
        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("pipes", self.tempdir_path)
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that default is SVG
        self.assertTrue(logo_fn.suffix == ".svg")
        # Check that the file is valid svg
        with open(logo_fn) as fh:
            svg = fh.read()
            self.assertTrue("<svg" in svg)
            # Check that the file contains the text
            self.assertTrue("pipes" in svg)
            # Check that default is light theme
            self.assertTrue("rgb(250,250,250)" not in svg)
            self.assertTrue("rgb(5,5,5)" in svg)
            # check the default width
            self.assertTrue('width="2300.0px"' in svg)

    def test_create_logo_dark_svg(self):
        """Test that the create-logo command works with the dark theme"""
        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("testpipeline", self.tempdir_path, theme="dark")
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that default is SVG
        self.assertTrue(logo_fn.suffix == ".svg")
        # Check that the file is valid svg
        with open(logo_fn) as fh:
            svg = fh.read()
            self.assertTrue("<svg" in svg)
            # Check that the file contains the text
            self.assertTrue("testpipeline" in svg)
            # Check that default is light theme
            self.assertTrue("rgb(250,250,250)" in svg)
            self.assertTrue("rgb(5,5,5)" not in svg)

    def test_create_logo_dark_png(self):
        """Test that the create-logo command works with the dark theme and pngs"""
        # create a light theme logo
        logo_fn = nf_core.create_logo.Logo().create("testpipeline", self.tempdir_path, theme="light", format="png")
        # create a dark theme logo
        logo_dark_fn = nf_core.create_logo.Logo().create("testpipeline", self.tempdir_path, theme="dark", format="png")
        # Check that the file exists
        self.assertTrue(logo_dark_fn.is_file())
        # Check that the file is a PNG
        self.assertTrue(logo_dark_fn.suffix == ".png")
        # check that the dark theme logo is larger than the light theme logo
        self.assertTrue(logo_dark_fn.stat().st_size > logo_fn.stat().st_size)

    def test_create_logo_small(self):
        """Test that the create-logo command works with the width parameter"""
        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("test", self.tempdir_path, width=600)
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that the file is valid svg
        with open(logo_fn) as fh:
            svg = fh.read()
            self.assertTrue("<svg" in svg)
            # check the  width
            self.assertTrue('width="600.0px"' in svg)

    def test_missing_text(self):
        """Test that the create-logo command raises an info when no text is provided"""
        with self.assertRaises(UserWarning):
            nf_core.create_logo.Logo().create("", self.tempdir_path)

    def test_recreation_no_force(self):
        """Test that the create-logo command fails when the logo already exists"""
        # create a logo
        nf_core.create_logo.Logo().create("testpipeline", self.tempdir_path, theme="light")
        # check that a info messages is logged when the logo already exists, without failing
        with self.assertLogs(nf_core.create_logo.__name__, level="INFO") as cm:
            nf_core.create_logo.Logo().create("testpipeline", self.tempdir_path, theme="light")
            self.assertIn("Logo already exists at", cm.output[0])

    def test_force_creation(self):
        """Test that the force flag works"""
        # create a logo
        logo_fn = nf_core.create_logo.Logo().create("testpipeline", self.tempdir_path, theme="light")
        copyfile(logo_fn, logo_fn.parent / "test.svg")
        logo_fn = logo_fn.parent / "test.svg"
        # create the same logo again, with force
        logo_fn_new = nf_core.create_logo.Logo().create("testpipeline", self.tempdir_path, force=True)
        # check that the file has a different creation time
        self.assertTrue(logo_fn.stat().st_ctime != logo_fn_new.stat().st_ctime)
        # check that the file has the same size
        self.assertTrue(logo_fn.stat().st_size == logo_fn_new.stat().st_size)
