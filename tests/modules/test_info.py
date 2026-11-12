from pathlib import Path

import yaml
from rich.console import Console

import nf_core.modules.info

from ..test_modules import TestModules
from ..utils import GITLAB_DEFAULT_BRANCH, GITLAB_URL


class TestModulesCreate(TestModules):
    def test_modules_info_remote(self):
        """Test getting info about a remote module"""
        mods_info = nf_core.modules.info.ModuleInfo(self.pipeline_dir, "fastqc")
        mods_info_output = mods_info.get_component_info()
        console = Console(record=True)
        console.print(mods_info_output)
        output = console.export_text()

        assert "Module: fastqc" in output
        assert "Inputs" in output
        assert "Outputs" in output

    def test_modules_info_remote_gitlab(self):
        """Test getting info about a module in the remote gitlab repo"""
        mods_info = nf_core.modules.info.ModuleInfo(
            self.pipeline_dir, "fastqc", remote_url=GITLAB_URL, branch=GITLAB_DEFAULT_BRANCH
        )
        mods_info_output = mods_info.get_component_info()
        console = Console(record=True)
        console.print(mods_info_output)
        output = console.export_text()

        assert "Module: fastqc" in output
        assert "Inputs" in output
        assert "Outputs" in output
        assert "--git-remote" in output

    def test_modules_info_local(self):
        """Test getting info about a locally installed module"""
        self.mods_install.install("trimgalore")
        mods_info = nf_core.modules.info.ModuleInfo(self.pipeline_dir, "trimgalore")
        mods_info_output = mods_info.get_component_info()
        console = Console(record=True)
        console.print(mods_info_output)
        output = console.export_text()

        assert "Module: trimgalore" in output
        assert "Inputs" in output
        assert "Outputs" in output
        assert "Location" in output

    def test_modules_info_in_modules_repo(self):
        """Test getting info about a module in the modules repo"""
        mods_info = nf_core.modules.info.ModuleInfo(self.nfcore_modules, "fastqc")
        mods_info.local = True
        mods_info_output = mods_info.get_component_info()
        console = Console(record=True)
        console.print(mods_info_output)
        output = console.export_text()

        assert "Module: fastqc" in output
        assert "Inputs" in output
        assert "Outputs" in output

    def test_modules_info_mixed_input_type(self):
        """Test getting info about a module with mixed input types (list and dict)"""
        self.mods_install.install("fastqc")
        meta_path = Path(self.pipeline_dir, "modules", "nf-core", "fastqc", "meta.yml")

        # Load existing meta.yml
        with open(meta_path) as f:
            meta = yaml.safe_load(f)

        # Append a dictionary-style input (the cause of the bug)
        meta["input"].append({"index_format": {"type": "string", "description": "Index format"}})

        # Write modified meta.yml back
        with open(meta_path, "w") as f:
            yaml.dump(meta, f)

        mods_info = nf_core.modules.info.ModuleInfo(self.pipeline_dir, "fastqc")
        mods_info_output = mods_info.get_component_info()
        console = Console(record=True)
        console.print(mods_info_output)
        output = console.export_text()

        assert "Module: fastqc" in output
        assert "index_format" in output
        assert "(string)" in output
