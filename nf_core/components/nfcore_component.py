"""
The NFCoreComponent class holds information and utility functions for a single module or subworkflow
"""
from pathlib import Path


class NFCoreComponent:
    """
    A class to hold the information about a nf-core module or subworkflow.
    Includes functionality for linting.
    """

    def __init__(
        self, component_name, repo_url, component_dir, repo_type, base_dir, component_type, remote_component=True
    ):
        """
        Initialize the object

        Args:
            component_name (str): The name of the module or subworkflow
            repo_url (str): The URL of the repository
            component_dir (Path): The absolute path to the module or subworkflow
            repo_type (str): Either 'pipeline' or 'modules' depending on
                             whether the directory is a pipeline or clone
                             of nf-core/modules.
            base_dir (Path): The absolute path to the pipeline base dir
            component_type (str): Either 'modules' or 'subworkflows'
            remote_component (bool): Whether the module is to be treated as a
                                     nf-core or local component
        """
        self.component_name = component_name
        self.repo_url = repo_url
        self.component_dir = component_dir
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

        if remote_component:
            # Initialize the important files
            self.main_nf = self.component_dir / "main.nf"
            self.meta_yml = self.component_dir / "meta.yml"

            repo_dir = self.component_dir.parts[: self.component_dir.parts.index(self.component_name.split("/")[0])][-1]
            self.org = repo_dir
            self.test_dir = Path(self.base_dir, "tests", component_type, repo_dir, self.component_name)
            self.test_yml = self.test_dir / "test.yml"
            self.test_main_nf = self.test_dir / "main.nf"

            if self.repo_type == "pipeline":
                patch_fn = f"{self.component_name.replace('/', '-')}.diff"
                patch_path = Path(self.component_dir, patch_fn)
                if patch_path.exists():
                    self.is_patched = True
                    self.patch_path = patch_path
        else:
            # The main file is just the local module
            self.main_nf = self.component_dir
            self.component_name = self.component_dir.stem
            # These attributes are only used by nf-core modules
            # so just initialize them to None
            self.meta_yml = None
            self.test_dir = None
            self.test_yml = None
            self.test_main_nf = None
