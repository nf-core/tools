"""Some tests covering the pipeline creation sub command."""
# import json
# import os
# import tempfile
# import unittest
#
# import pytest
# from rich.console import Console
#
# import nf_core.create
# import nf_core.licences

# TODO nf-core: Assess and strip out if no longer required for DSL2

# class WorkflowLicensesTest(unittest.TestCase):
#     """A class that performs tests on the workflow license
#     retrieval functionality of nf-core tools."""

#     def setUp(self):
#         """ Create a new pipeline, then make a Licence object """
#         # Set up the schema
#         self.pipeline_dir = os.path.join(tempfile.mkdtemp(), "test_pipeline")
#         self.create_obj = nf_core.create.PipelineCreate("testing", "test pipeline", "tester", outdir=self.pipeline_dir)
#         self.create_obj.init_pipeline()
#         self.license_obj = nf_core.licences.WorkflowLicences(self.pipeline_dir)

#     def test_run_licences_successful(self):
#         console = Console(record=True)
#         console.print(self.license_obj.run_licences())
#         output = console.export_text()
#         assert "GPL v3" in output

#     def test_run_licences_successful_json(self):
#         self.license_obj.as_json = True
#         console = Console(record=True)
#         console.print(self.license_obj.run_licences())
#         output = json.loads(console.export_text())
#         for package in output:
#             if "multiqc" in package:
#                 assert output[package][0] == "GPL v3"
#                 break
#         else:
#             raise LookupError("Could not find MultiQC")

#     def test_get_environment_file_local(self):
#         self.license_obj.get_environment_file()
#         assert any(["multiqc" in k for k in self.license_obj.conda_config["dependencies"]])

#     def test_get_environment_file_remote(self):
#         self.license_obj = nf_core.licences.WorkflowLicences("methylseq")
#         self.license_obj.get_environment_file()
#         assert any(["multiqc" in k for k in self.license_obj.conda_config["dependencies"]])

#     @pytest.mark.xfail(raises=LookupError, strict=True)
#     def test_get_environment_file_nonexistent(self):
#         self.license_obj = nf_core.licences.WorkflowLicences("fubarnotreal")
#         self.license_obj.get_environment_file()
