#!/usr/bin/env python
""" Tests covering the refgenie integration code
"""

import os
import unittest
import tempfile
import subprocess
import shlex

import nf_core.refgenie


class TestRefgenie(unittest.TestCase):
    """Class for refgenie tests"""

    def setUp(self):
        """
        Prepare a refgenie config file
        """
        self.tmp_dir = tempfile.mkdtemp()
        self.NXF_HOME = os.path.join(self.tmp_dir, ".nextflow")
        self.NXF_REFGENIE_PATH = os.path.join(self.NXF_HOME, "nf-core", "refgenie_genomes.config")
        self.REFGENIE = os.path.join(self.tmp_dir, "genomes_config.yaml")

        # create NXF_HOME and nf-core directories
        os.makedirs(os.path.join(self.NXF_HOME, "nf-core"), exist_ok=True)

        # Initialize a refgenie config
        os.system(f"refgenie init -c {self.REFGENIE}")

        # Add NXF_REFGENIE_PATH to refgenie config
        with open(self.REFGENIE, "a") as fh:
            fh.write(f"nextflow_config: {os.path.join(self.NXF_REFGENIE_PATH)}\n")

    def tearDown(self) -> None:
        # Remove the tempdir again
        os.system(f"rm -rf {self.tmp_dir}")

    def test_update_refgenie_genomes_config(self):
        """Test that listing pipelines works"""
        # Populate the config with a genome
        cmd = f"refgenie pull t7/fasta -c {self.REFGENIE}"
        out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)

        assert "Updated nf-core genomes config" in str(out)
