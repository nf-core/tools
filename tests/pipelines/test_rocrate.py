"""Test the nf-core pipelines rocrate command"""

import shutil
from pathlib import Path

import rocrate.rocrate
from git import Repo

import nf_core.pipelines.create
import nf_core.pipelines.create.create
import nf_core.pipelines.rocrate
import nf_core.utils

from ..test_pipelines import TestPipelines


class TestROCrate(TestPipelines):
    """Class for lint tests"""

    def setUp(self) -> None:
        super().setUp()
        # add fake metro map
        Path(self.pipeline_dir, "docs", "images", "nf-core-testpipeline_metro_map.png").touch()
        # commit the changes
        repo = Repo(self.pipeline_dir)
        repo.git.add(A=True)
        repo.index.commit("Initial commit")

    def tearDown(self):
        """Clean up temporary files and folders"""

        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def test_rocrate_creation(self):
        """Run the nf-core rocrate command"""

        # Run the command
        self.rocrate_obj = nf_core.pipelines.rocrate.ROCrate(self.test_pipeline_dir)
        self.rocrate_obj.create_rocrate(self.test_pipeline_dir, metadata_path=Path(self.test_pipeline_dir))

        # Check that the crate was created
        self.assertTrue(Path(self.test_pipeline_dir, "ro-crate-metadata.json").exists())

        # Check that the entries in the crate are correct
        crate = rocrate.rocrate.ROCrate(self.test_pipeline_dir)
        entities = crate.get_entities()

        # Check if the correct entities are set:
        for entity in entities:
            entity_json = entity.as_jsonld()
            if entity_json["@id"] == "./":
                self.assertEqual(entity_json.get("name"), "nf-core/testpipeline")
                self.assertEqual(entity_json["mainEntity"], {"@id": "main.nf"})
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
