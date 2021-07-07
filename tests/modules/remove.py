import os


def test_modules_remove_trimgalore(self):
    """Test removing TrimGalore! module after installing it"""
    self.mods_install.install("trimgalore")
    module_path = os.path.join(self.mods_install.dir, "modules", "nf-core", "modules", "trimgalore")
    assert self.mods_remove.remove("trimgalore")
    assert os.path.exists(module_path) is False


def test_modules_remove_trimgalore_uninstalled(self):
    """Test removing TrimGalore! module without installing it"""
    assert self.mods_remove.remove("trimgalore") is False


# TODO Remove comments once external repository to have same structure as nf-core/modules
# def test_modules_remove_trimgalore_alternative_source(self):
#     """Test removing TrimGalore! module after installing it from an alternative source"""
#     self.mods_install_alt.install("trimgalore")
#     module_path = os.path.join(self.mods_install.dir, "modules", "external", "trimgalore")
#     assert self.mods_remove_alt.remove("trimgalore")
#     assert os.path.exists(module_path) is False
