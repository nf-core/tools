import importlib
import os
from unittest import mock

import responses

import nf_core.components.components_utils

from ..test_components import TestComponents
from ..utils import mock_biotools_api_calls


def test_get_components_to_install_full_path_subworkflow(tmp_path):
    """Full-path includes pointing to subworkflows should preserve underscores."""
    main_nf = tmp_path / "main.nf"
    main_nf.write_text("include { VCF_GATHER_BCFTOOLS } from '../../../subworkflows/nf-core/vcf_gather_bcftools'\n")
    modules, subworkflows = nf_core.components.components_utils.get_components_to_install(tmp_path)
    assert len(subworkflows) == 1
    assert subworkflows[0]["name"] == "vcf_gather_bcftools"
    assert len(modules) == 0


def test_get_components_to_install_full_path_module(tmp_path):
    """Full-path includes pointing to modules should convert underscores to slashes."""
    main_nf = tmp_path / "main.nf"
    main_nf.write_text("include { SAMTOOLS_SORT } from '../../../modules/nf-core/samtools/sort'\n")
    modules, subworkflows = nf_core.components.components_utils.get_components_to_install(tmp_path)
    assert len(modules) == 1
    assert modules[0]["name"] == "samtools/sort"
    assert len(subworkflows) == 0


def test_get_components_to_install_relative_subworkflow(tmp_path):
    """Relative includes (../) should be treated as subworkflows with underscores preserved."""
    main_nf = tmp_path / "main.nf"
    main_nf.write_text("include { VCF_GATHER_BCFTOOLS } from '../vcf_gather_bcftools'\n")
    modules, subworkflows = nf_core.components.components_utils.get_components_to_install(tmp_path)
    assert len(subworkflows) == 1
    assert subworkflows[0]["name"] == "vcf_gather_bcftools"
    assert len(modules) == 0


def test_get_components_to_install_mixed_includes(tmp_path):
    """A main.nf with both module and subworkflow full-path includes should be parsed correctly."""
    main_nf = tmp_path / "main.nf"
    main_nf.write_text(
        "include { SAMTOOLS_SORT } from '../../../modules/nf-core/samtools/sort'\n"
        "include { VCF_GATHER_BCFTOOLS } from '../../../subworkflows/nf-core/vcf_gather_bcftools'\n"
        "include { BAM_MARKDUPLICATES } from '../bam_markduplicates'\n"
    )
    modules, subworkflows = nf_core.components.components_utils.get_components_to_install(tmp_path)
    assert len(modules) == 1
    assert modules[0]["name"] == "samtools/sort"
    assert len(subworkflows) == 2
    sw_names = {sw["name"] for sw in subworkflows}
    assert sw_names == {"vcf_gather_bcftools", "bam_markduplicates"}


class TestTestComponentsUtils(TestComponents):
    def test_get_biotools_id(self):
        """Test getting the bio.tools ID for a tool"""
        with responses.RequestsMock() as rsps:
            mock_biotools_api_calls(rsps, "bpipe")
            response = nf_core.components.components_utils.get_biotools_response("bpipe")
            id = nf_core.components.components_utils.get_biotools_id(response, "bpipe")
            assert id == "biotools:bpipe"

    def test_get_biotools_id_warn(self):
        """Test getting the bio.tools ID for a tool and failing"""
        with responses.RequestsMock() as rsps:
            mock_biotools_api_calls(rsps, "bpipe")
            response = nf_core.components.components_utils.get_biotools_response("bpipe")
            nf_core.components.components_utils.get_biotools_id(response, "test")
            assert "Could not find a bio.tools ID for 'test'" in self.caplog.text

    def test_get_biotools_ch_info(self):
        """Test getting the bio.tools channel information for a tool"""
        with responses.RequestsMock() as rsps:
            mock_biotools_api_calls(rsps, "bpipe")
            response = nf_core.components.components_utils.get_biotools_response("bpipe")
            inputs, outputs = nf_core.components.components_utils.get_channel_info_from_biotools(response, "bpipe")
            assert inputs == {
                "raw_sequence": (
                    [
                        "http://edamontology.org/data_0848",
                        "http://edamontology.org/format_2182",
                        "http://edamontology.org/format_2573",
                    ],
                    ["Raw sequence", "FASTQ-like format (text)", "SAM"],
                    ["fastq-like", "sam"],
                )
            }
            assert outputs == {
                "sequence_report": (
                    ["http://edamontology.org/data_2955", "http://edamontology.org/format_2331"],
                    ["Sequence report", "HTML"],
                    ["html"],
                )
            }

    def test_get_biotools_ch_info_warn(self):
        """Test getting the bio.tools channel information for a tool and failing"""
        with responses.RequestsMock() as rsps:
            mock_biotools_api_calls(rsps, "bpipe")
            response = nf_core.components.components_utils.get_biotools_response("bpipe")
            nf_core.components.components_utils.get_channel_info_from_biotools(response, "test")
            assert "Could not find an EDAM ontology term for 'test'" in self.caplog.text

    def test_environment_variables_override(self):
        """Test environment variables override default values"""
        mock_env = {
            "NF_CORE_MODULES_NAME": "custom-name",
            "NF_CORE_MODULES_REMOTE": "https://custom-repo.git",
            "NF_CORE_MODULES_DEFAULT_BRANCH": "custom-branch",
        }

        try:
            with mock.patch.dict(os.environ, mock_env):
                importlib.reload(nf_core.components.constants)
                assert nf_core.components.constants.NF_CORE_MODULES_NAME == mock_env["NF_CORE_MODULES_NAME"]
                assert nf_core.components.constants.NF_CORE_MODULES_REMOTE == mock_env["NF_CORE_MODULES_REMOTE"]
                assert (
                    nf_core.components.constants.NF_CORE_MODULES_DEFAULT_BRANCH
                    == mock_env["NF_CORE_MODULES_DEFAULT_BRANCH"]
                )
        finally:
            importlib.reload(nf_core.components.constants)
