import nf_core.modules.modules_utils

from ..test_modules import TestModules


class TestModulesUtils(TestModules):
    def test_get_installed_modules(self):
        """Test getting installed modules"""
        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)
        assert len(nfcore_modules) == 1
        assert nfcore_modules[0].component_name == "bpipe/test"

    def test_get_installed_modules_with_files(self):
        """Test getting installed modules. When a module contains a file in its directory, it shouldn't be picked up as a tool/subtool"""
        # Create a file in the module directory
        with open(self.nfcore_modules / "modules" / "nf-core" / "bpipe" / "test_file.txt", "w") as fh:
            fh.write("test")

        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)
        assert len(nfcore_modules) == 1
