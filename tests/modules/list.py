import nf_core.modules
from rich.console import Console


def test_modules_list_remote(self):
    """Test listing available modules"""
    mods_list = nf_core.modules.ModuleList(None, remote=True)
    listed_mods = mods_list.list_modules()
    console = Console(record=True)
    console.print(listed_mods)
    output = console.export_text()
    assert "fastqc" in output


def test_modules_list_pipeline(self):
    """Test listing locally installed modules"""
    mods_list = nf_core.modules.ModuleList(self.pipeline_dir, remote=False)
    listed_mods = mods_list.list_modules()
    console = Console(record=True)
    console.print(listed_mods)
    output = console.export_text()
    assert "fastqc" in output
    assert "multiqc" in output


def test_modules_install_and_list_pipeline(self):
    """Test listing locally installed modules"""
    self.mods_install.install("trimgalore")
    mods_list = nf_core.modules.ModuleList(self.pipeline_dir, remote=False)
    listed_mods = mods_list.list_modules()
    console = Console(record=True)
    console.print(listed_mods)
    output = console.export_text()
    assert "trimgalore" in output
