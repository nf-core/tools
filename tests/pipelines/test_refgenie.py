"""Tests covering the refgenie integration code"""

import os
import shlex
import subprocess
import tempfile
import unittest


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
        self.translation_file = os.path.join(self.tmp_dir, "alias_translations.yaml")
        # Set NXF_HOME environment variable
        # avoids adding includeConfig statement to config file outside the current tmpdir
        try:
            self.NXF_HOME_ORIGINAL = os.environ["NXF_HOME"]
        except Exception:
            self.NXF_HOME_ORIGINAL = None
        os.environ["NXF_HOME"] = self.NXF_HOME

        # create NXF_HOME and nf-core directories
        os.makedirs(os.path.join(self.NXF_HOME, "nf-core"), exist_ok=True)

        # Initialize a refgenie config
        os.system(f"refgenie init -c {self.REFGENIE}")

        # Add NXF_REFGENIE_PATH to refgenie config
        with open(self.REFGENIE, "a") as fh:
            fh.write(f"nextflow_config: {os.path.join(self.NXF_REFGENIE_PATH)}\n")

        # Add an alias translation to YAML file
        with open(self.translation_file, "a") as fh:
            fh.write("ensembl_gtf: gtf\n")

    def tearDown(self) -> None:
        # Remove the tempdir again
        os.system(f"rm -rf {self.tmp_dir}")
        # Reset NXF_HOME environment variable
        if self.NXF_HOME_ORIGINAL is None:
            del os.environ["NXF_HOME"]
        else:
            os.environ["NXF_HOME"] = self.NXF_HOME_ORIGINAL

    def test_update_refgenie_genomes_config(self):
        """Test that listing pipelines works"""
        # Populate the config with a genome
        cmd = f"refgenie pull t7/fasta -c {self.REFGENIE}"
        out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)

        assert "Updated nf-core genomes config" in str(out)

    def test_asset_alias_translation(self):
        """Test that asset aliases are translated correctly"""
        # Populate the config with a genome
        cmd = f"refgenie pull hg38/ensembl_gtf -c {self.REFGENIE}"
        subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
        cmd = f"cat {self.NXF_REFGENIE_PATH}"
        out = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
        assert "      gtf                  = " in str(out)
        assert "      ensembl_gtf          = " not in str(out)
