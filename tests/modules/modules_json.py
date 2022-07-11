import os
import shutil

import nf_core.modules.modules_json
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME


def test_create_modules_json(self):
    """Test creating a modules.json file from scratch""" ""
    mod_json_path = os.path.join(self.pipeline_dir, "modules.json")
    # Remove the existing modules.json file
    os.remove(mod_json_path)

    # Create the new modules.json file
    # (There are no prompts as long as there are only nf-core modules)
    nf_core.modules.modules_json.ModulesJson(self.pipeline_dir).create_modules_json()

    # Check that the file exists
    assert os.path.exists(mod_json_path)

    # Get the contents of the file
    mod_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    mod_json = mod_json_obj.get_modules_json()

    mods = ["fastqc", "multiqc"]
    for mod in mods:
        assert mod in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]
        assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][mod]


def test_get_pipeline_module_repositories(self):
    """Check that the pipeline repositories are correctly retrieved"""
    pass
