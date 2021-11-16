"""
The NFCoreModule class holds information and utility functions for a single module
"""
import os


class NFCoreModule(object):
    """
    A class to hold the information about a nf-core module
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
        self.git_sha = None

        if nf_core_module:
            # Initialize the important files
            self.main_nf = os.path.join(self.module_dir, "main.nf")
            self.meta_yml = os.path.join(self.module_dir, "meta.yml")
            self.function_nf = os.path.join(self.module_dir, "functions.nf")
            if self.repo_type == "pipeline":
                self.module_name = module_dir.split("nf-core/modules" + os.sep)[1]
            else:
                if "modules/modules" in module_dir:
                    self.module_name = module_dir.split("modules/modules" + os.sep)[1]
                else:
                    self.module_name = module_dir.split("modules" + os.sep)[1]

            self.test_dir = os.path.join(self.base_dir, "tests", "modules", self.module_name)
            self.test_yml = os.path.join(self.test_dir, "test.yml")
            self.test_main_nf = os.path.join(self.test_dir, "main.nf")
