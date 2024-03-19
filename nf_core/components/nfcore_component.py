"""
The NFCoreComponent class holds information and utility functions for a single module or subworkflow
"""

import logging
import re
from pathlib import Path
from typing import Union

log = logging.getLogger(__name__)


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
            self.main_nf = Path(self.component_dir, "main.nf")
            self.meta_yml = Path(self.component_dir, "meta.yml")
            self.process_name = ""
            self.environment_yml = Path(self.component_dir, "environment.yml")

            repo_dir = self.component_dir.parts[: self.component_dir.parts.index(self.component_name.split("/")[0])][-1]
            self.org = repo_dir
            self.nftest_testdir = Path(self.component_dir, "tests")
            self.nftest_main_nf = Path(self.nftest_testdir, "main.nf.test")
            self.tags_yml = Path(self.nftest_testdir, "tags.yml")

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
            self.meta_yml = ""
            self.environment_yml = ""
            self.test_dir = None
            self.test_yml = None
            self.test_main_nf = None

    def _get_main_nf_tags(self, test_main_nf: Union[Path, str]):
        """Collect all tags from the main.nf.test file."""
        tags = []
        with open(test_main_nf) as fh:
            for line in fh:
                if line.strip().startswith("tag"):
                    tags.append(line.strip().split()[1].strip('"'))
        return tags

    def _get_included_components(self, main_nf: Union[Path, str]):
        """Collect all included components from the main.nf file."""
        included_components = []
        with open(main_nf) as fh:
            for line in fh:
                if line.strip().startswith("include"):
                    # get tool/subtool or subworkflow name from include statement, can be in the form
                    #'../../../modules/nf-core/hisat2/align/main'
                    #'../bam_sort_stats_samtools/main'
                    #'../subworkflows/nf-core/bam_sort_stats_samtools/main'
                    #'plugin/nf-validation'
                    component = line.strip().split()[-1].split(self.org)[-1].split("main")[0].strip("/")
                    component = component.replace("'../", "subworkflows/")
                    component = component.replace("'", "")
                    included_components.append(component)
        return included_components

    def _get_included_components_in_chained_tests(self, main_nf_test: Union[Path, str]):
        """Collect all included components from the main.nf file."""
        included_components = []
        with open(main_nf_test) as fh:
            for line in fh:
                if line.strip().startswith("script"):
                    # get tool/subtool or subworkflow name from script statement, can be:
                    # if the component is a module TOOL/SUBTOOL:
                    # '../../SUBTOOL/main.nf'
                    # '../../../TOOL/SUBTOOL/main.nf'
                    # '../../../TOOL/main.nf'
                    # if the component is a module TOOL:
                    # '../../TOOL/main.nf'
                    # '../../TOOL/SUBTOOL/main.nf'
                    # if the component uses full paths or is a subworkflow:
                    # '(../../)modules/nf-core/TOOL/(SUBTOOL/)main.nf'
                    # '(../../)subworkflows/nf-core/TOOL/(SUBTOOL/)main.nf'
                    # the line which uses the current component script:
                    # '../main.nf'
                    component = (
                        line.strip()
                        .split("../")[-1]
                        .split(self.org)[-1]
                        .split("main.nf")[0]
                        .strip("'")
                        .strip('"')
                        .strip("/")
                    )
                    if (
                        "/" in self.component_name
                        and "/" not in component
                        and line.count("../") == 2
                        and self.org not in line
                        and component != ""
                    ):
                        # Add the current component name "TOOL" to the tag
                        component = f"{self.component_name.split('/')[0]}/{component}"
                    if "subworkflows" in line:
                        # Add the subworkflows prefix to the tag
                        component = f"subworkflows/{component}"
                    if component != "":
                        included_components.append(component)
        return included_components

    def get_inputs_from_main_nf(self):
        """Collect all inputs from the main.nf file."""
        inputs = []
        with open(self.main_nf) as f:
            data = f.read()
        # get input values from main.nf after "input:", which can be formatted as tuple val(foo) path(bar) or val foo or val bar or path bar or path foo
        # regex matches:
        # val(foo)
        # path(bar)
        # val foo
        # val bar
        # path bar
        # path foo
        # don't match anything inside comments or after "output:"
        if "input:" not in data:
            log.debug(f"Could not find any inputs in {self.main_nf}")
            return inputs
        input_data = data.split("input:")[1].split("output:")[0]
        regex = r"(val|path)\s*(\(([^)]+)\)|\s*([^)\s,]+))"
        matches = re.finditer(regex, input_data, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            if match.group(3):
                input_val = match.group(3).split(",")[0]  # handle `files, stageAs: "inputs/*"` cases
                inputs.append(input_val)
            elif match.group(4):
                input_val = match.group(4).split(",")[0]  # handle `files, stageAs: "inputs/*"` cases
                inputs.append(input_val)
        log.debug(f"Found {len(inputs)} inputs in {self.main_nf}")
        self.inputs = inputs

    def get_outputs_from_main_nf(self):
        outputs = []
        with open(self.main_nf) as f:
            data = f.read()
        # get output values from main.nf after "output:". the names are always after "emit:"
        if "output:" not in data:
            log.debug(f"Could not find any outputs in {self.main_nf}")
            return outputs
        output_data = data.split("output:")[1].split("when:")[0]
        regex = r"emit:\s*([^)\s,]+)"
        matches = re.finditer(regex, output_data, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            outputs.append(match.group(1))
        log.debug(f"Found {len(outputs)} outputs in {self.main_nf}")
        self.outputs = outputs
