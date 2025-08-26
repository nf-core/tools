"""
Classes for updating and correcting meta.yml files in nf-core modules.

This module provides specialized classes for different aspects of meta.yml file updates:
- MetaInfoFinder: Handles finding metadata information in complex nested structures
- EdamOntologyManager: Manages EDAM ontology detection and addition
- BiotoolsIdentifierManager: Manages bio.tools identifier updates
- InputOutputCorrector: Manages input/output structure corrections
- MetaYmlUpdater: Main orchestrator class that coordinates all updates
"""

import logging
import re
from functools import lru_cache
from typing import Any, Union

import ruamel.yaml

import nf_core.modules.modules_utils
from nf_core.components.components_utils import get_biotools_id, get_biotools_response, yaml
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.pipelines.lint_utils import run_prettier_on_file

log = logging.getLogger(__name__)

# Global cache for EDAM formats to avoid repeated network calls
_edam_cache = None


def get_cached_edam_formats() -> dict[str, list[str]]:
    """
    Get EDAM formats with caching to avoid repeated network calls.

    This optimization addresses the performance issue where each module
    would load EDAM formats independently, causing significant slowdown.

    Returns:
        dict: Cached EDAM format mappings
    """
    global _edam_cache
    if _edam_cache is None:
        log.debug("Loading EDAM formats (first time, will be cached)")
        _edam_cache = nf_core.modules.modules_utils.load_edam()
    else:
        log.debug("Using cached EDAM formats")
    return _edam_cache


@lru_cache(maxsize=256)
def get_biotools_response_cached(tool_name: str) -> dict | None:
    """
    Get bio.tools response with LRU caching to avoid repeated API calls.

    This optimization caches bio.tools API responses to prevent the same
    tool from being queried multiple times during a linting session.

    Args:
        tool_name: Name of the tool to query

    Returns:
        dict: Bio.tools API response or None if not found
    """
    log.debug(f"Getting bio.tools response for {tool_name} (with caching)")
    return get_biotools_response(tool_name)


class MetaInfoFinder:
    """Handles finding metadata information in complex nested meta.yml structures."""

    @staticmethod
    def find_meta_info(meta_yml: Union[list, dict], element_name: str, is_output: bool = False) -> dict[str, Any]:
        """
        Find the information specified in the meta.yml file to update the corrected meta.yml content.

        Args:
            meta_yml: The meta.yml structure to search in
            element_name: Name of the element to find
            is_output: Whether this is output metadata (affects list->dict conversion)

        Returns:
            Dict containing the found metadata, empty dict if not found
        """
        if is_output and isinstance(meta_yml, list):
            # Convert old meta.yml structure for outputs (list) to dict
            meta_yml = {k: v for d in meta_yml for k, v in d.items()}

        if isinstance(meta_yml, list):
            return MetaInfoFinder._search_in_list_structure(meta_yml, element_name)
        elif isinstance(meta_yml, dict):
            return MetaInfoFinder._search_in_dict_structure(meta_yml, element_name)

        return {}

    @staticmethod
    def _search_in_list_structure(meta_yml: list, element_name: str) -> dict[str, Any]:
        """Search for element in list-based meta.yml structure."""
        for k, meta_channel in enumerate(meta_yml):
            if isinstance(meta_channel, list):
                for x, meta_element in enumerate(meta_channel):
                    if element_name == list(meta_element.keys())[0]:
                        return meta_yml[k][x][element_name]
            elif isinstance(meta_channel, dict):
                if element_name == list(meta_channel.keys())[0]:
                    return meta_yml[k][element_name]
        return {}

    @staticmethod
    def _search_in_dict_structure(meta_yml: dict, element_name: str) -> dict[str, Any]:
        """Search for element in dict-based meta.yml structure."""
        for ch_name, channels in meta_yml.items():
            for k, meta_channel in enumerate(channels):
                if isinstance(meta_channel, list):
                    for x, meta_element in enumerate(meta_channel):
                        if element_name == list(meta_element.keys())[0]:
                            return meta_yml[ch_name][k][x][element_name]
                elif isinstance(meta_channel, dict):
                    if element_name == list(meta_channel.keys())[0]:
                        return meta_yml[ch_name][k][element_name]
        return {}


class EdamOntologyManager:
    """Manages EDAM ontology detection and addition for meta.yml sections."""

    def __init__(self, edam_formats: dict[str, list[str]]):
        """
        Initialize the EDAM ontology manager.

        Args:
            edam_formats: Dictionary mapping file extensions to EDAM format information
        """
        self.edam_formats = edam_formats

    def add_edam_ontologies(self, section: dict[str, Any], desc: str) -> None:
        """
        Add EDAM ontologies to a meta.yml section based on file patterns.

        Args:
            section: The meta.yml section to update
            desc: Description for logging purposes
        """
        expected_ontologies = self._extract_expected_ontologies(section)
        current_ontologies = self._extract_current_ontologies(section, desc)

        self._ensure_ontologies_section_exists(section)
        self._add_missing_ontologies(section, expected_ontologies, current_ontologies, desc)

    def _extract_expected_ontologies(self, section: dict[str, Any]) -> list[tuple[str, str]]:
        """Extract expected ontologies from file patterns."""
        expected_ontologies: list[tuple[str, str]] = []

        if "pattern" not in section:
            return expected_ontologies

        pattern = section["pattern"]

        # Check pattern detection and process for different cases
        if re.search(r"{", pattern):
            for extension in re.split(r",|{|}", pattern):
                if extension in self.edam_formats:
                    expected_ontologies.append((self.edam_formats[extension][0], extension))
        else:
            if re.search(r"\.\w+$", pattern):
                extension = pattern.split(".")[-1]
                if extension in self.edam_formats:
                    expected_ontologies.append((self.edam_formats[extension][0], extension))

        # Remove duplicated entries
        return list({k: v for k, v in expected_ontologies}.items())

    def _extract_current_ontologies(self, section: dict[str, Any], desc: str) -> list[str]:
        """Extract current ontologies from the section."""
        current_ontologies = []

        if "ontologies" in section:
            for ontology in section["ontologies"]:
                try:
                    current_ontologies.append(ontology["edam"])
                except KeyError:
                    log.warning(f"Could not add ontologies in {desc}: {ontology}")

        return current_ontologies

    def _ensure_ontologies_section_exists(self, section: dict[str, Any]) -> None:
        """Ensure the ontologies section exists for file types."""
        if "ontologies" not in section and "type" in section and section["type"] == "file":
            section["ontologies"] = []

    def _add_missing_ontologies(
        self,
        section: dict[str, Any],
        expected_ontologies: list[tuple[str, str]],
        current_ontologies: list[str],
        desc: str,
    ) -> None:
        """Add missing ontologies to the section."""
        log.debug(f"expected ontologies for {desc}: {expected_ontologies}")
        log.debug(f"current ontologies for {desc}: {current_ontologies}")

        for ontology, ext in expected_ontologies:
            if ontology not in current_ontologies:
                try:
                    section["ontologies"].append(ruamel.yaml.comments.CommentedMap({"edam": ontology}))
                    section["ontologies"][-1].yaml_add_eol_comment(f"{self.edam_formats[ext][1]}", "edam")
                except KeyError:
                    log.warning(f"Could not add ontologies in {desc}")


class BiotoolsIdentifierManager:
    """Manages bio.tools identifier updates for tools in meta.yml."""

    @staticmethod
    def add_biotools_identifiers(tools_section: list[dict[str, Any]]) -> None:
        """
        Add bio.tools identifiers to tools that don't have them.

        Args:
            tools_section: The tools section from meta.yml
        """
        for i, tool in enumerate(tools_section):
            tool_name = list(tool.keys())[0]
            if "identifier" not in tool[tool_name]:
                biotools_data = get_biotools_response_cached(tool_name)
                if biotools_data is not None:
                    tools_section[i][tool_name]["identifier"] = get_biotools_id(biotools_data, tool_name)


class InputOutputCorrector:
    """Manages input/output structure corrections in meta.yml."""

    def __init__(self, meta_info_finder: MetaInfoFinder):
        """
        Initialize the input/output corrector.

        Args:
            meta_info_finder: Instance of MetaInfoFinder for metadata lookups
        """
        self.meta_info_finder = meta_info_finder

    def correct_inputs(
        self, corrected_meta_yml: dict[str, Any], original_meta_yml: dict[str, Any], mod_inputs: list[Any]
    ) -> None:
        """
        Correct input structure in meta.yml.

        Args:
            corrected_meta_yml: The corrected meta.yml structure being built
            original_meta_yml: The original meta.yml content
            mod_inputs: The inputs from main.nf
        """
        corrected_meta_yml["input"] = mod_inputs.copy()

        for i, channel in enumerate(corrected_meta_yml["input"]):
            if isinstance(channel, list):
                for j, element in enumerate(channel):
                    element_name = list(element.keys())[0]
                    corrected_meta_yml["input"][i][j][element_name] = self.meta_info_finder.find_meta_info(
                        original_meta_yml["input"], element_name
                    )
            elif isinstance(channel, dict):
                element_name = list(channel.keys())[0]
                corrected_meta_yml["input"][i][element_name] = self.meta_info_finder.find_meta_info(
                    original_meta_yml["input"], element_name
                )

    def correct_outputs(
        self,
        corrected_meta_yml: dict[str, Any],
        original_meta_yml: dict[str, Any],
        mod_outputs: Union[list[str], dict[str, Any]],
    ) -> None:
        """
        Correct output structure in meta.yml.

        Args:
            corrected_meta_yml: The corrected meta.yml structure being built
            original_meta_yml: The original meta.yml content
            mod_outputs: The outputs from main.nf
        """
        corrected_meta_yml["output"] = mod_outputs.copy()

        for ch_name in corrected_meta_yml["output"].keys():
            for i, ch_content in enumerate(corrected_meta_yml["output"][ch_name]):
                if isinstance(ch_content, list):
                    for j, element in enumerate(ch_content):
                        element_name = list(element.keys())[0]
                        corrected_meta_yml["output"][ch_name][i][j][element_name] = (
                            self.meta_info_finder.find_meta_info(
                                original_meta_yml["output"], element_name, is_output=True
                            )
                        )
                elif isinstance(ch_content, dict):
                    element_name = list(ch_content.keys())[0]
                    corrected_meta_yml["output"][ch_name][i][element_name] = self.meta_info_finder.find_meta_info(
                        original_meta_yml["output"], element_name, is_output=True
                    )


class MetaYmlUpdater:
    """Main orchestrator class for updating meta.yml files."""

    def __init__(self, module: NFCoreComponent):
        """
        Initialize the meta.yml updater.

        Args:
            module: The nf-core component to update
        """
        self.module = module
        self.meta_info_finder = MetaInfoFinder()
        self.input_output_corrector = InputOutputCorrector(self.meta_info_finder)

        # Load EDAM formats with caching and initialize ontology manager
        edam_formats = get_cached_edam_formats()
        self.edam_ontology_manager = EdamOntologyManager(edam_formats)

    def update_meta_yml_file(self, read_meta_yml_func, obtain_inputs_func, obtain_outputs_func) -> None:
        """
        Update the meta.yml file with correct inputs, outputs, ontologies, and bio.tools identifiers.

        Args:
            read_meta_yml_func: Function to read meta.yml content
            obtain_inputs_func: Function to obtain input structure
            obtain_outputs_func: Function to obtain output structure
        """
        meta_yml = read_meta_yml_func(self.module)
        corrected_meta_yml = meta_yml.copy()

        # Update inputs and outputs if needed
        self._update_inputs_outputs(meta_yml, corrected_meta_yml, obtain_inputs_func, obtain_outputs_func)

        # Add EDAM ontologies
        self._add_edam_ontologies_to_corrected_meta(corrected_meta_yml)

        # Add bio.tools identifiers
        BiotoolsIdentifierManager.add_biotools_identifiers(corrected_meta_yml["tools"])

        # Write the updated file
        self._write_updated_meta_yml(corrected_meta_yml)

    def _update_inputs_outputs(
        self, meta_yml: dict[str, Any], corrected_meta_yml: dict[str, Any], obtain_inputs_func, obtain_outputs_func
    ) -> None:
        """Update inputs and outputs if they differ from main.nf."""
        # Handle inputs
        if "input" in meta_yml:
            correct_inputs = obtain_inputs_func(self.module.inputs)
            meta_inputs = obtain_inputs_func(meta_yml["input"])

            if correct_inputs != meta_inputs:
                log.debug(
                    f"Correct inputs: '{correct_inputs}' differ from current inputs: "
                    f"'{meta_inputs}' in '{self.module.meta_yml}'"
                )
                self.input_output_corrector.correct_inputs(corrected_meta_yml, meta_yml, self.module.inputs)

        # Handle outputs
        if "output" in meta_yml:
            correct_outputs = obtain_outputs_func(self.module.outputs)
            meta_outputs = obtain_outputs_func(meta_yml["output"])

            if correct_outputs != meta_outputs:
                log.debug(
                    f"Correct outputs: '{correct_outputs}' differ from current outputs: "
                    f"'{meta_outputs}' in '{self.module.meta_yml}'"
                )
                self.input_output_corrector.correct_outputs(corrected_meta_yml, meta_yml, self.module.outputs)

    def _add_edam_ontologies_to_corrected_meta(self, corrected_meta_yml: dict[str, Any]) -> None:
        """Add EDAM ontologies to inputs and outputs."""
        # Add ontologies to inputs
        if "input" in corrected_meta_yml:
            for i, channel in enumerate(corrected_meta_yml["input"]):
                if isinstance(channel, list):
                    for j, element in enumerate(channel):
                        element_name = list(element.keys())[0]
                        self.edam_ontology_manager.add_edam_ontologies(
                            corrected_meta_yml["input"][i][j][element_name], f"input - {element_name}"
                        )
                elif isinstance(channel, dict):
                    element_name = list(channel.keys())[0]
                    self.edam_ontology_manager.add_edam_ontologies(
                        corrected_meta_yml["input"][i][element_name], f"input - {element_name}"
                    )

        # Add ontologies to outputs
        if "output" in corrected_meta_yml:
            for ch_name in corrected_meta_yml["output"].keys():
                ch_content = corrected_meta_yml["output"][ch_name][0]
                if isinstance(ch_content, list):
                    for i, element in enumerate(ch_content):
                        element_name = list(element.keys())[0]
                        self.edam_ontology_manager.add_edam_ontologies(
                            corrected_meta_yml["output"][ch_name][0][i][element_name],
                            f"output - {ch_name} - {element_name}",
                        )
                elif isinstance(ch_content, dict):
                    element_name = list(ch_content.keys())[0]
                    self.edam_ontology_manager.add_edam_ontologies(
                        corrected_meta_yml["output"][ch_name][0][element_name], f"output - {ch_name} - {element_name}"
                    )

    def _write_updated_meta_yml(self, corrected_meta_yml: dict[str, Any]) -> None:
        """Write the updated meta.yml file to disk."""
        if self.module.meta_yml is not None:
            with open(self.module.meta_yml, "w") as fh:
                log.info(f"Updating {self.module.meta_yml}")
                yaml.dump(corrected_meta_yml, fh)
                run_prettier_on_file(fh.name)
