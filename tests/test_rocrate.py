""" Test the nf-core rocrate command """


import shutil
import tempfile
import unittest
from pathlib import Path

import rocrate.rocrate
from git import Repo

import nf_core.create
import nf_core.rocrate
import nf_core.utils


class TestROCrate(unittest.TestCase):
    """Class for lint tests"""

    def setUp(self):
        """Function that runs at start of tests for common resources

        Use nf_core.create() to make a pipeline that we can use for testing
        """

        self.tmp_dir = Path(tempfile.mkdtemp())
        self.test_pipeline_dir = Path(self.tmp_dir, "nf-core-testpipeline")
        self.create_obj = nf_core.create.PipelineCreate(
            name="testpipeline",
            description="This is a test pipeline",
            author="Test McTestFace",
            outdir=self.test_pipeline_dir,
            version="1.0.0",
            no_git=False,
            force=True,
            plain=True,
        )
        self.create_obj.init_pipeline()

        # add fake metro map
        Path(self.test_pipeline_dir, "docs", "images", "nf-core-testpipeline_metro_map.png").touch()
        # commit the changes
        repo = Repo(self.test_pipeline_dir)
        repo.git.add(A=True)
        repo.index.commit("Initial commit")

    def tearDown(self):
        """Clean up temporary files and folders"""

        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def test_rocrate_creation(self):
        """Run the nf-core rocrate command"""

        # Run the command
        self.rocrate_obj = nf_core.rocrate.ROCrate(self.test_pipeline_dir)
        self.rocrate_obj.create_ro_crate(self.test_pipeline_dir, metadata_path=Path(self.test_pipeline_dir))

        # Check that the crate was created
        self.assertTrue(Path(self.test_pipeline_dir, "ro-crate-metadata.json").exists())

        # Check that the entries in the crate are correct
        crate = rocrate.rocrate.ROCrate(self.test_pipeline_dir)
        entities = crate.get_entities()

        # Check if the correct entities are set:
        for entity in entities:
            entity_json = entity.as_jsonld()
            if entity_json["@id"] == "./":
                self.assertEqual(entity_json.get("name"), "Research Object Crate for nf-core/testpipeline")
                self.assertEqual(entity_json["mainEntity"], {"@id": "#main.nf"})
            elif entity_json["@id"] == "#main.nf":
                self.assertEqual(entity_json["programmingLanguage"], [{"@id": "#nextflow"}])
                self.assertEqual(entity_json["image"], [{"@id": "nf-core-testpipeline_metro_map.png"}])
            # assert there is a metro map
            # elif entity_json["@id"] == "nf-core-testpipeline_metro_map.png": # FIXME waiting for https://github.com/ResearchObject/ro-crate-py/issues/174
            # self.assertEqual(entity_json["@type"], ["File", "ImageObject"])
            # assert that author is set as a person
            elif "name" in entity_json and entity_json["name"] == "Test McTestFace":
                self.assertEqual(entity_json["@type"], "Person")
                # check that it is set as author of the main entity
                if crate.mainEntity is not None:
                    self.assertEqual(crate.mainEntity["author"][0].id, entity_json["@id"])
