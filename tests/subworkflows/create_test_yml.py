import os
from unittest import mock

import pytest

import nf_core.subworkflows

from ..utils import with_temporary_folder


@with_temporary_folder
def test_subworkflows_custom_yml_dumper(self, out_dir):
    """Try to create a yml file with the custom yml dumper"""
    yml_output_path = os.path.join(out_dir, "test.yml")
    meta_builder = nf_core.subworkflows.SubworkflowTestYmlBuilder(
        subworkflow="test/tool",
        directory=self.pipeline_dir,
        test_yml_output_path=yml_output_path,
        no_prompts=True,
    )
    meta_builder.test_yml_output_path = yml_output_path
    meta_builder.tests = [{"testname": "myname"}]
    meta_builder.print_test_yml()
    assert os.path.isfile(yml_output_path)
