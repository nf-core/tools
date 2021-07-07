import tempfile
import pytest
import os


def test_modules_install_nopipeline(self):
    """Test installing a module - no pipeline given"""
    self.mods_install.dir = None
    assert self.mods_install.install("foo") is False


def test_modules_install_emptypipeline(self):
    """Test installing a module - empty dir given"""
    self.mods_install.dir = tempfile.mkdtemp()
    with pytest.raises(UserWarning) as excinfo:
        self.mods_install.install("foo")
    assert "Could not find a 'main.nf' or 'nextflow.config' file" in str(excinfo.value)


def test_modules_install_nomodule(self):
    """Test installing a module - unrecognised module given"""
    assert self.mods_install.install("foo") is False


def test_modules_install_trimgalore(self):
    """Test installing a module - TrimGalore!"""
    assert self.mods_install.install("trimgalore") is not False
    module_path = os.path.join(self.mods_install.dir, "modules", "nf-core", "modules", "trimgalore")
    assert os.path.exists(module_path)


def test_modules_install_trimgalore_alternative_source(self):
    """Test installing a module from a different source repository - TrimGalore!"""
    assert self.mods_install_alt.install("trimgalore") is not False
    module_path = os.path.join(self.mods_install.dir, "modules", "external", "trimgalore")
    assert os.path.exists(module_path)


def test_modules_install_trimgalore_twice(self):
    """Test installing a module - TrimGalore! already there"""
    self.mods_install.install("trimgalore")
    assert self.mods_install.install("trimgalore") is True
