import responses

import nf_core.components.components_utils

from ..test_components import TestComponents
from ..utils import mock_biotools_api_calls


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
                    ["fastq-like", "sam"],
                )
            }
            assert outputs == {
                "sequence_report": (
                    ["http://edamontology.org/data_2955", "http://edamontology.org/format_2331"],
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
