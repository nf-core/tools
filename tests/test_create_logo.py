"""Test covering the create-logo command."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import nf_core.create_logo


def assert_images_equal(image_1: Path, image_2: Path):
    img1 = Image.open(image_1)
    img2 = Image.open(image_2)

    # Convert to same mode and size for comparison
    img2 = img2.convert(img1.mode)
    img2 = img2.resize(img1.size)

    sum_sq_diff = np.sum((np.asarray(img1).astype("float") - np.asarray(img2).astype("float")) ** 2)

    if sum_sq_diff == 0:
        # Images are exactly the same
        pass
    else:
        normalized_sum_sq_diff = sum_sq_diff / np.sqrt(sum_sq_diff)
        assert normalized_sum_sq_diff < 0.001


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
        assert_images_equal(logo_fn, Path("tests/fixtures/create_logo.png"))

    def test_create_logo_png_dark(self):
        """Test that the create-logo command works for dark PNGs"""

        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("pipes", self.tempdir_path, theme="dark")
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that the file is a PNG
        self.assertTrue(logo_fn.suffix == ".png")
        assert_images_equal(logo_fn, Path("tests/fixtures/create_logo_dark.png"))

    def test_create_log_png_width(self):
        """Test that the create-logo command works for PNGs with a custom width"""

        # Create a logo
        logo_fn = nf_core.create_logo.Logo().create("pipes", self.tempdir_path, width=100)
        # Check that the file exists
        self.assertTrue(logo_fn.is_file())
        # Check that the file is a PNG
        self.assertTrue(logo_fn.suffix == ".png")
        assert_images_equal(logo_fn, Path("tests/fixtures/create_logo_width100.png"))
