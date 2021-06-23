"""
The NFCoreModule class holds information and uitily functions for a single module
"""
import os


class NFCoreModule(object):
    """
    A class to hold the information a bout a nf-core module
    Includes functionality for linting
    """

    def __init__(self, module_dir, repo_type, base_dir, nf_core_module=True):
        self.module_dir = module_dir
        self.repo_type = repo_type
        self.base_dir = base_dir
        self.passed = []
        self.warned = []
        self.failed = []
        self.inputs = []
        self.outputs = []
        self.has_meta = False

        if nf_core_module:
            # Initialize the important files
            self.main_nf = os.path.join(self.module_dir, "main.nf")
            self.meta_yml = os.path.join(self.module_dir, "meta.yml")
            self.function_nf = os.path.join(self.module_dir, "functions.nf")
            self.software = self.module_dir.split("software" + os.sep)[1]
            self.test_dir = os.path.join(self.base_dir, "tests", "software", self.software)
            self.test_yml = os.path.join(self.test_dir, "test.yml")
            self.test_main_nf = os.path.join(self.test_dir, "main.nf")
            self.module_name = module_dir.split("software" + os.sep)[1]
