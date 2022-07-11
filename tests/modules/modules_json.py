import json
import os

from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME


def test_create(self):
    """Test creating a modules.json file from scratch""" ""
    mod_json_path = os.path.join(self.pipeline_dir, "modules.json")
    # Remove the existing modules.json file
    os.remove(mod_json_path)

    # Create the new modules.json file
    # (There are no prompts as long as there are only nf-core modules)
    ModulesJson(self.pipeline_dir).create()

    # Check that the file exists
    assert os.path.exists(mod_json_path)

    # Get the contents of the file
    mod_json_obj = nf_core.modules.modules_json.ModulesJson(self.pipeline_dir)
    mod_json = mod_json_obj.get_modules_json()

    mods = ["fastqc", "multiqc"]
    for mod in mods:
        assert mod in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]
        assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"][mod]


def test_up_to_date(self):
    """
    Checks if the modules.json file is up to date
    when no changes have been made to the pipeline
    """
    mod_json_obj = ModulesJson(self.pipeline_dir)
    mod_json_before = mod_json_obj.get_modules_json()
    mod_json_obj.up_to_date()
    mod_json_after = mod_json_obj.get_modules_json()

    # Check that the modules.json hasn't changed
    mods = ["fastqc", "multiqc"]
    for mod in mods:
        assert mod in mod_json_after["repos"][NF_CORE_MODULES_NAME]["modules"]
        assert "git_sha" in mod_json_after["repos"][NF_CORE_MODULES_NAME]["modules"][mod]
        assert (
            mod_json_before["repos"][NF_CORE_MODULES_NAME]["modules"][mod]["git_sha"]
            == mod_json_after["repos"][NF_CORE_MODULES_NAME]["modules"][mod]["git_sha"]
        )


def test__json_up_to_date_entry_removed(self):
    """
    Makes the modules.json up to date when a module
    entry has been removed
    """
    # Remove the fastqc entry from the modules.json file
    with open(os.path.join(self.pipeline_dir, "modules.json"), "r") as f:
        mod_json = json.load(f)
    entry = mod_json["repos"][NF_CORE_MODULES_NAME]["modules"].pop("fastqc")
    with open(os.path.join(self.pipeline_dir, "modules.json"), "w") as f:
        json.dump(mod_json, f, indent=4)

    # Check that the modules.json file is up to date, and regenerate the entry
    mod_json_obj = ModulesJson(self.pipeline_dir)
    mod_json_obj.up_to_date()
    mod_json = mod_json_obj.get_modules_json()

    # Check that the entry has been regenerated
    assert "fastqc" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]
    assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["fastqc"]
    assert entry["git_sha"] == mod_json["repos"][NF_CORE_MODULES_NAME]["modules"]["fastqc"]["git_sha"]
