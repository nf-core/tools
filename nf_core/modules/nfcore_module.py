"""
The NFCoreModule class holds information and utility functions for a single module
"""
from pathlib import Path


class NFCoreModule(object):
    """
    A class to hold the information about a nf-core module
    Includes functionality for linting
    """

    def __init__(self, module_name, repo_name, module_dir, repo_type, base_dir, nf_core_module=True):
        """
        Initialize the object

        Args:
            module_dir (Path): The absolute path to the module
            repo_type (str): Either 'pipeline' or 'modules' depending on
                             whether the directory is a pipeline or clone
                             of nf-core/modules.
            base_dir (Path): The absolute path to the pipeline base dir
            nf_core_module (bool): Whether the module is to be treated as a
                                   nf-core or local module
        """
        self.module_name = module_name
        self.repo_name = repo_name
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
        self.is_patched = False
        self.is_patched = None

        if nf_core_module:
            # Initialize the important files
            self.main_nf = self.module_dir / "main.nf"
            self.meta_yml = self.module_dir / "meta.yml"

            self.test_dir = Path(self.base_dir, "tests", "modules", self.module_name)
            self.test_yml = self.test_dir / "test.yml"
            self.test_main_nf = self.test_dir / "main.nf"

            if self.repo_type == "pipeline":
                patch_fn = f"{self.module_name.replace('/', '-')}.diff"
                patch_path = Path(self.module_dir, patch_fn)
                if patch_path.exists():
                    self.is_patched = True
                    self.patch_path = patch_path
        else:
            # The main file is just the local module
            self.main_nf = self.module_dir
            self.module_name = self.module_dir.stem
            # These attributes are only used by nf-core modules
            # so just initialize them to None
            self.meta_yml = None
            self.test_dir = None
            self.test_yml = None
            self.test_main_nf = None
