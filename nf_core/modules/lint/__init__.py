"""
Code for linting modules in the nf-core/modules repository and
in nf-core pipelines

Command:
nf-core modules lint
"""

import json
import logging
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import questionary
import rich
import rich.progress
import ruamel.yaml

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.components_utils import get_biotools_id, get_biotools_response, yaml
from nf_core.components.lint import ComponentLint, LintExceptionError, LintResult
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.pipelines.lint_utils import console, run_prettier_on_file
from nf_core.utils import unquote

log = logging.getLogger(__name__)

from .environment_yml import environment_yml
from .main_nf import main_nf
from .meta_yml import meta_yml, obtain_inputs, obtain_outputs, obtain_topics, read_meta_yml
from .module_changes import module_changes
from .module_deprecations import module_deprecations
from .module_patch import module_patch
from .module_tests import module_tests
from .module_todos import module_todos
from .module_version import module_version


class ModuleLint(ComponentLint):
    """
    An object for linting modules either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    # Import lint functions
    environment_yml = environment_yml
    main_nf = main_nf
    meta_yml = meta_yml
    obtain_inputs = obtain_inputs
    obtain_outputs = obtain_outputs
    obtain_topics = obtain_topics
    read_meta_yml = read_meta_yml
    module_changes = module_changes
    module_deprecations = module_deprecations
    module_patch = module_patch
    module_tests = module_tests
    module_todos = module_todos
    module_version = module_version

    def __init__(
        self,
        directory: str | Path,
        fail_warned: bool = False,
        fix: bool = False,
        remote_url: str | None = None,
        branch: str | None = None,
        no_pull: bool = False,
        registry: str | None = None,
        hide_progress: bool = False,
    ):
        super().__init__(
            component_type="modules",
            directory=directory,
            fail_warned=fail_warned,
            fix=fix,
            remote_url=remote_url,
            branch=branch,
            no_pull=no_pull,
            registry=registry,
            hide_progress=hide_progress,
        )
        self.meta_schema: Mapping[str, Any] | None = None

    def lint(
        self,
        module=None,
        registry="quay.io",
        key=(),
        all_modules=False,
        print_results=True,
        show_passed=False,
        sort_by="test",
        local=False,
        fix_version=False,
        plain_text=False,
    ):
        """
        Lint all or one specific module

        First gets a list of all local modules (in modules/local/process) and all modules
        installed from nf-core (in modules/nf-core)

        For all nf-core modules, the correct file structure is assured and important
        file content is verified. If directory subject to linting is a clone of 'nf-core/modules',
        the files necessary for testing the modules are also inspected.

        For all local modules, the '.nf' file is checked for some important flags, and warnings
        are issued if untypical content is found.

        :param module:          A specific module to lint
        :param print_results:   Whether to print the linting results
        :param show_passed:     Whether passed tests should be shown as well
        :param fix_version:     Update the module version if a newer version is available
        :param hide_progress:   Don't show progress bars
        :param plain_text:      Print output in plain text without rich formatting

        :returns:               A ModuleLint object containing information of
                                the passed, warned and failed tests
        """
        # TODO: consider unifying modules and subworkflows lint() function and add it to the ComponentLint class
        # Prompt for module or all
        if module is None and not (local or all_modules) and len(self.all_remote_components) > 0:
            questions = [
                {
                    "type": "list",
                    "name": "all_modules",
                    "message": "Lint all modules or a single named module?",
                    "choices": ["All modules", "Named module"],
                },
                {
                    "type": "autocomplete",
                    "name": "tool_name",
                    "message": "Tool name:",
                    "when": lambda x: x["all_modules"] == "Named module",
                    "choices": [m.component_name for m in self.all_remote_components],
                },
            ]
            answers = questionary.unsafe_prompt(questions, style=nf_core.utils.nfcore_question_style)
            all_modules = answers["all_modules"] == "All modules"
            module = answers.get("tool_name")

        # Only lint the given module
        if module:
            if all_modules:
                raise LintExceptionError("You cannot specify a tool and request all tools to be linted.")
            local_modules = []
            remote_modules = nf_core.modules.modules_utils.filter_modules_by_name(self.all_remote_components, module)
            if len(remote_modules) == 0:
                raise LintExceptionError(f"Could not find the specified module: '{module}'")
        else:
            local_modules = self.all_local_components
            remote_modules = self.all_remote_components

        if self.repo_type == "modules":
            log.info(f"Linting modules repo: [magenta]'{self.directory}'")
        else:
            log.info(f"Linting pipeline: [magenta]'{self.directory}'")
        if module:
            log.info(f"Linting module: [magenta]'{module}'")

        # Filter the tests by the key if one is supplied
        if key:
            self.filter_tests_by_key(key)
            log.info("Only running tests: '{}'".format("', '".join(key)))

        # If it is a pipeline, load the lint config file and the modules.json file
        if self.repo_type == "pipeline":
            self.set_up_pipeline_files()

        # Lint local modules
        if local and len(local_modules) > 0:
            self.lint_modules(local_modules, registry=registry, local=True, fix_version=fix_version)

        # Lint nf-core modules
        if not local and len(remote_modules) > 0:
            self.lint_modules(remote_modules, registry=registry, local=False, fix_version=fix_version)

        if print_results:
            self._print_results(show_passed=show_passed, sort_by=sort_by, plain_text=plain_text)
            self.print_summary(plain_text=plain_text)

    def lint_modules(
        self, modules: list[NFCoreComponent], registry: str = "quay.io", local: bool = False, fix_version: bool = False
    ) -> None:
        """
        Lint a list of modules

        Args:
            modules ([NFCoreComponent]): A list of module objects
            registry (str): The container registry to use. Should be quay.io in most situations.
            local (boolean): Whether the list consist of local or nf-core modules
            fix_version (boolean): Fix the module version if a newer version is available
        """
        # TODO: consider unifying modules and subworkflows lint_modules() function and add it to the ComponentLint class
        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
            console=console,
            disable=self.hide_progress or os.environ.get("HIDE_PROGRESS", None) is not None,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                f"Linting {'local' if local else 'nf-core'} modules",
                total=len(modules),
                test_name=modules[0].component_name,
            )

            for mod in modules:
                progress_bar.update(lint_progress, advance=1, test_name=mod.component_name)
                self.lint_module(mod, progress_bar, local=local, fix_version=fix_version)

    def lint_module(
        self,
        mod: NFCoreComponent,
        progress_bar: rich.progress.Progress,
        local: bool = False,
        fix_version: bool = False,
    ):
        """
        Perform linting on one module

        If the module is a local module we only check the `main.nf` file,
        and issue warnings instead of failures.

        If the module is a nf-core module we check for existence of the files
        - main.nf
        - meta.yml
        And verify that their content conform to the nf-core standards.

        If the linting is run for modules in the central nf-core/modules repo
        (repo_type==modules), files that are relevant for module testing are
        also examined
        """
        # TODO: consider unifying modules and subworkflows lint_module() function and add it to the ComponentLint class
        # Only check the main script in case of a local module
        if local:
            mod.get_inputs_from_main_nf()
            mod.get_outputs_from_main_nf()
            mod.get_topics_from_main_nf()
            # Update meta.yml file if requested
            if self.fix and mod.meta_yml is not None:
                self.update_meta_yml_file(mod)

            for test_name in self.lint_tests:
                if test_name in self.local_module_exclude_tests:
                    continue
                if test_name == "main_nf":
                    getattr(self, test_name)(mod, fix_version, self.registry, progress_bar)
                elif test_name in ["meta_yml", "environment_yml"]:
                    # Allow files to be missing for local
                    getattr(self, test_name)(mod, allow_missing=True)
                else:
                    getattr(self, test_name)(mod)

            self.passed += [LintResult(mod, *m) for m in mod.passed]
            warned = [LintResult(mod, *m) for m in (mod.warned + mod.failed)]
            if not self.fail_warned:
                self.warned += warned
            else:
                self.failed += warned

        # Otherwise run all the lint tests
        else:
            mod.get_inputs_from_main_nf()
            mod.get_outputs_from_main_nf()
            mod.get_topics_from_main_nf()
            # Update meta.yml file if requested
            if self.fix:
                self.update_meta_yml_file(mod)

            if self.repo_type == "pipeline" and self.modules_json and mod.repo_url:
                # Set correct sha
                version = self.modules_json.get_module_version(mod.component_name, mod.repo_url, mod.org)
                mod.git_sha = version

            for test_name in self.lint_tests:
                if test_name == "main_nf":
                    getattr(self, test_name)(mod, fix_version, self.registry, progress_bar)
                else:
                    getattr(self, test_name)(mod)

            self.passed += [LintResult(mod, *m) for m in mod.passed]
            warned = [LintResult(mod, *m) for m in mod.warned]
            if not self.fail_warned:
                self.warned += warned
            else:
                self.failed += warned

            self.failed += [LintResult(mod, *m) for m in mod.failed]

    def load_meta_schema(self) -> Mapping[str, Any]:
        """
        Load the meta.yml JSON schema from the local modules repository cache.
        The schema is cached in self.meta_schema to avoid reloading.

        Returns:
            dict: The meta.yml JSON schema

        Raises:
            LookupError: If the local module cache is not found
        """
        # Return cached schema if already loaded
        if self.meta_schema is not None:
            return self.meta_schema

        if self.modules_repo.local_repo_dir is None:
            raise LookupError("Local module cache not found")

        with open(Path(self.modules_repo.local_repo_dir, "modules/meta-schema.json")) as fh:
            self.meta_schema = json.load(fh)
        return self.meta_schema

    def update_meta_yml_file(self, mod):
        """
        Update the meta.yml file with the correct inputs and outputs
        """
        meta_yml = self.read_meta_yml(mod)
        if meta_yml is None:
            log.warning(f"Could not read meta.yml for {mod.component_name}, skipping update")
            return
        corrected_meta_yml = meta_yml.copy()

        def _find_meta_info(meta_yml: dict, element_name: str, is_output=False) -> dict:
            """Find the information specified in the meta.yml file to update the corrected meta.yml content

            Note: element_name may contain quotes (e.g., '"*.html"', "'bpipe'") from parsing main.nf,
            but meta.yml keys don't include the quotes. We normalize both for comparison
            by removing paired quotes (both single and double).
            """
            # Remove paired quotes (single or double) from element name for comparison
            normalized_element_name = unquote(element_name)

            # Convert old meta.yml output structure (list) to dict
            if is_output and isinstance(meta_yml, list):
                meta_yml = {k: v for d in meta_yml for k, v in d.items()}

            # Helper to check if a key matches and return its metadata
            def check_match(element: dict) -> dict | None:
                key = list(element.keys())[0]
                return element[key] if normalized_element_name == unquote(key) else None

            # Handle list structure (inputs)
            if isinstance(meta_yml, list):
                for channel in meta_yml:
                    if isinstance(channel, list):
                        for element in channel:
                            if (result := check_match(element)) is not None:
                                return result
                    elif isinstance(channel, dict) and (result := check_match(channel)) is not None:
                        return result

            # Handle dict structure (outputs/topics)
            elif isinstance(meta_yml, dict):
                for channels in meta_yml.values():
                    for channel in channels:
                        if isinstance(channel, list):
                            for element in channel:
                                if (result := check_match(element)) is not None:
                                    return result
                        elif isinstance(channel, dict) and (result := check_match(channel)) is not None:
                            return result

            return {}

        def _sort_meta_yml(meta_yml: dict) -> dict:
            """Sort meta.yml keys according to the schema's property order"""
            # Get the schema to determine the correct key order
            try:
                schema = self.load_meta_schema()
                schema_keys = list(schema["properties"].keys())
            except (LintExceptionError, KeyError) as e:
                raise UserWarning("Failed to load meta schema", e)

            result: dict = {}

            # First, add keys in the order they appear in the schema
            for key in schema_keys:
                if key in meta_yml:
                    result[key] = meta_yml[key]

            # Then add any keys that aren't in the schema (to preserve custom keys)
            for key in meta_yml.keys():
                if key not in result:
                    result[key] = meta_yml[key]

            return result

        # Obtain inputs, outputs and topics from main.nf and meta.yml
        # Used to compare only the structure of channels and elements
        # Do not compare features to allow for custom features in meta.yml (i.e. pattern)
        if "input" in meta_yml:
            correct_inputs = self.obtain_inputs(mod.inputs)
            meta_inputs = self.obtain_inputs(meta_yml["input"])
        if "output" in meta_yml:
            correct_outputs = self.obtain_outputs(mod.outputs)
            meta_outputs = self.obtain_outputs(meta_yml["output"])

        correct_topics = self.obtain_topics(mod.topics)
        meta_topics = self.obtain_topics(meta_yml.get("topics", {}))

        # Load topic metadata template from module-template/meta.yml
        template_path = Path(__file__).parent.parent.parent / "module-template" / "meta.yml"
        topic_metadata = [{}, {}, {}]  # [process, tool, version]
        try:
            with open(template_path) as fh:
                template_meta = yaml.load(fh)
                versions_entry = template_meta.get("topics", {}).get("versions", [[]])[0]
                if len(versions_entry) == 3:
                    topic_metadata = [next(iter(item.values())) for item in versions_entry]
        except Exception as e:
            log.debug(f"Could not load topic template metadata: {e}")

        def _populate_channel_elements(io_type, correct_value, meta_value, mod_io_data, meta_yml_io, check_exists=True):
            """Populate input, output, or topic channel elements with metadata information.

            Args:
                io_type: "input", "output", or "topics" string for logging
                correct_value: The correct value to compare against
                meta_value: The current meta.yml value
                mod_io_data: The module's input/output/topics data structure
                meta_yml_io: The original meta.yml input/output/topics section
                check_exists: If True, only process if io_type exists in meta_yml (for input/output).
                             If False, process if correct_value exists (for topics that can be added).

            Returns:
                Populated data structure or None if no changes needed
            """
            # Check if we should process this section
            if check_exists:
                # For input/output: only process if already exists in meta.yml
                if io_type not in meta_yml or correct_value == meta_value:
                    return None
            else:
                # For topics: process if correct_value exists (can add new topics)
                if not correct_value or correct_value == meta_value:
                    return None

            log.debug(
                f"Correct {io_type}s: '{correct_value}' differ from current {io_type}s: '{meta_value}' in '{mod.meta_yml}'"
            )

            def _process_element(element, index, is_output=False):
                """Process a single element: normalize name, get metadata, adjust for topics."""
                element_name = list(element.keys())[0]
                normalized_name = unquote(element_name)
                # Ensure normalized_name is always a string (e.g., convert 1.2 -> "1.2")
                normalized_name = str(normalized_name)
                element_meta = _find_meta_info(meta_yml_io, element_name, is_output=is_output)

                # For topics, handle type field based on keyword
                if io_type == "topics":
                    keyword = element.get(element_name, {}).get("_keyword", "")

                    # If no existing metadata, use template defaults
                    if not element_meta:
                        element_meta = topic_metadata[index].copy() if index < len(topic_metadata) else {}
                        log.debug(f"Adding topic metadata for '{normalized_name}' at index {index}: {element_meta}")

                    # Adjust type field based on keyword (val -> string, eval -> eval)
                    if keyword == "val" and "type" in element_meta:
                        element_meta["type"] = "string"
                    elif keyword == "eval" and "type" in element_meta:
                        element_meta["type"] = "eval"

                return normalized_name, element_meta

            corrected_data = mod_io_data.copy()

            if io_type == "input":
                # Input structure: [ [{meta:{}}, {bam:{}}], {reference:{}}] -> 2 channels
                for i, channel in enumerate(corrected_data):
                    if isinstance(channel, list):
                        for j, element in enumerate(channel):
                            normalized_name, element_meta = _process_element(element, j)
                            corrected_data[i][j] = {normalized_name: element_meta}
                    elif isinstance(channel, dict):
                        normalized_name, element_meta = _process_element(channel, i)
                        corrected_data[i] = {normalized_name: element_meta}
            else:
                # Output and topics structure: { name: [[ {meta:{}}, {*.bam:{}} ]], other: [ {*.fa:{}} ] }
                # Use the original meta_yml_io as the base to preserve all existing metadata
                # Only update structure when it differs from main.nf
                corrected_data = meta_yml_io.copy() if meta_yml_io else mod_io_data.copy()

                for ch_name in mod_io_data.keys():
                    # Ensure channel exists in corrected_data
                    if ch_name not in corrected_data:
                        corrected_data[ch_name] = []

                    # Resize corrected_data[ch_name] to match mod_io_data[ch_name] length
                    # This ensures we don't keep stale entries from old meta.yml
                    current_len = len(corrected_data[ch_name])
                    target_len = len(mod_io_data[ch_name])
                    if current_len < target_len:
                        corrected_data[ch_name].extend([[] for _ in range(target_len - current_len)])
                    elif current_len > target_len:
                        corrected_data[ch_name] = corrected_data[ch_name][:target_len]

                    for i, ch_content in enumerate(mod_io_data[ch_name]):
                        if isinstance(ch_content, list):
                            # Rebuild list with normalized keys
                            normalized_list = []
                            for j, element in enumerate(ch_content):
                                normalized_name, element_meta = _process_element(element, j, is_output=True)
                                normalized_list.append({normalized_name: element_meta})
                                log.debug(f"After assignment: normalized_list[{j}][{normalized_name}] = {element_meta}")
                            corrected_data[ch_name][i] = normalized_list
                        elif isinstance(ch_content, dict):
                            normalized_name, element_meta = _process_element(ch_content, i, is_output=True)
                            corrected_data[ch_name][i] = {normalized_name: element_meta}

            return corrected_data

        # Process inputs
        populated_inputs = _populate_channel_elements(
            "input", correct_inputs, meta_inputs, mod.inputs, meta_yml.get("input", {})
        )
        if populated_inputs is not None:
            corrected_meta_yml["input"] = populated_inputs

        # Process outputs
        populated_outputs = _populate_channel_elements(
            "output", correct_outputs, meta_outputs, mod.outputs, meta_yml.get("output", {})
        )
        if populated_outputs is not None:
            corrected_meta_yml["output"] = populated_outputs

        # Process topics (check_exists=False allows adding topics that don't exist in meta.yml yet)
        populated_topics = _populate_channel_elements(
            "topics", correct_topics, meta_topics, mod.topics, meta_yml.get("topics", {}), check_exists=False
        )
        if populated_topics is not None:
            corrected_meta_yml["topics"] = populated_topics

        # Populate metadata for versions_* output channels and topics (from template)
        def _populate_versions_metadata(section_name: str, section_data: dict) -> None:
            """Add template metadata to versions_* channels and topics.versions"""
            # Get the corresponding source data (mod.outputs or mod.topics) to check keywords
            source_data = mod.outputs if section_name == "output" else mod.topics

            for ch_name, ch_data in section_data.items():
                # Only process versions_* outputs or "versions" topic
                if (section_name == "output" and ch_name.startswith("versions_")) or (
                    section_name == "topics" and ch_name == "versions"
                ):
                    # Get source channel name (for topics, it's always "versions")
                    source_ch_name = "versions" if section_name == "topics" else ch_name
                    if source_ch_name not in source_data:
                        continue

                    for i, ch_content in enumerate(ch_data):
                        if isinstance(ch_content, list) and i < len(source_data[source_ch_name]):
                            for j, element in enumerate(ch_content):
                                element_name = list(element.keys())[0]
                                normalized_name = unquote(element_name)
                                element_meta = section_data[ch_name][i][j].get(normalized_name, {})

                                # Add metadata if empty
                                if not element_meta or not any(k in element_meta for k in ["type", "description"]):
                                    element_meta = topic_metadata[j].copy() if j < len(topic_metadata) else {}

                                # Check keyword from source data and adjust type
                                if isinstance(source_data[source_ch_name][i], list) and j < len(
                                    source_data[source_ch_name][i]
                                ):
                                    source_element = source_data[source_ch_name][i][j]
                                    source_element_name = list(source_element.keys())[0]
                                    keyword = source_element.get(source_element_name, {}).get("_keyword", "")
                                    if keyword == "val" and "type" in element_meta:
                                        element_meta["type"] = "string"
                                    elif keyword == "eval" and "type" in element_meta:
                                        element_meta["type"] = "eval"

                                section_data[ch_name][i][j][normalized_name] = element_meta
                                log.debug(
                                    f"Adding metadata to {section_name}.{ch_name} for '{normalized_name}' at index {j}"
                                )

        if "output" in corrected_meta_yml:
            _populate_versions_metadata("output", corrected_meta_yml["output"])
        if "topics" in corrected_meta_yml:
            _populate_versions_metadata("topics", corrected_meta_yml["topics"])

        def _add_edam_ontologies(section, edam_formats, desc):
            expected_ontologies = []
            current_ontologies = []
            if "pattern" in section:
                pattern = section["pattern"]
                # Check pattern detection and process for different cases
                if re.search(r"{", pattern):
                    for extension in re.split(r",|{|}", pattern):
                        if extension in edam_formats:
                            expected_ontologies.append((edam_formats[extension][0], extension))
                else:
                    if re.search(r"\.\w+$", pattern):
                        extension = pattern.split(".")[-1]
                        if extension in edam_formats:
                            expected_ontologies.append((edam_formats[extension][0], extension))
                # remove duplicated entries
                expected_ontologies = list({k: v for k, v in expected_ontologies}.items())
            if "ontologies" in section:
                for ontology in section["ontologies"]:
                    try:
                        current_ontologies.append(ontology["edam"])
                    except KeyError:
                        log.warning(f"Could not add ontologies in {desc}: {ontology}")
            elif "type" in section and section["type"] == "file":
                section["ontologies"] = []
            log.debug(f"expected ontologies for {desc}: {expected_ontologies}")
            log.debug(f"current ontologies for {desc}: {current_ontologies}")
            for ontology, ext in expected_ontologies:
                if ontology not in current_ontologies:
                    try:
                        section["ontologies"].append(ruamel.yaml.comments.CommentedMap({"edam": ontology}))
                        section["ontologies"][-1].yaml_add_eol_comment(f"{edam_formats[ext][1]}", "edam")
                    except KeyError:
                        log.warning(f"Could not add ontologies in {desc}")

        # EDAM ontologies
        edam_formats = nf_core.modules.modules_utils.load_edam()
        if "input" in meta_yml:
            for i, channel in enumerate(corrected_meta_yml["input"]):
                if isinstance(channel, list):
                    for j, element in enumerate(channel):
                        element_name = list(element.keys())[0]
                        _add_edam_ontologies(
                            corrected_meta_yml["input"][i][j][element_name], edam_formats, f"input - {element_name}"
                        )
                elif isinstance(channel, dict):
                    element_name = list(channel.keys())[0]
                    _add_edam_ontologies(
                        corrected_meta_yml["input"][i][element_name], edam_formats, f"input - {element_name}"
                    )

        if "output" in meta_yml:
            for ch_name in corrected_meta_yml["output"].keys():
                ch_content = corrected_meta_yml["output"][ch_name][0]
                if isinstance(ch_content, list):
                    for i, element in enumerate(ch_content):
                        element_name = list(element.keys())[0]
                        _add_edam_ontologies(
                            corrected_meta_yml["output"][ch_name][0][i][element_name],
                            edam_formats,
                            f"output - {ch_name} - {element_name}",
                        )
                elif isinstance(ch_content, dict):
                    element_name = list(ch_content.keys())[0]
                    _add_edam_ontologies(
                        corrected_meta_yml["output"][ch_name][0][element_name],
                        edam_formats,
                        f"output - {ch_name} - {element_name}",
                    )

        # Add bio.tools identifier
        for i, tool in enumerate(corrected_meta_yml["tools"]):
            tool_name = list(tool.keys())[0]
            if "identifier" not in tool[tool_name]:
                biotools_data = get_biotools_response(tool_name)
                corrected_meta_yml["tools"][i][tool_name]["identifier"] = get_biotools_id(biotools_data, tool_name)

        # Create YAML anchors for versions_* keys in output that match "versions" in topics
        # Since we now populate metadata for both output and topics, set up anchors to reference output from topics
        if "output" in corrected_meta_yml and "topics" in corrected_meta_yml:
            versions_keys = [key for key in corrected_meta_yml["output"].keys() if key.startswith("versions_")]

            if versions_keys and "versions" in corrected_meta_yml["topics"]:
                # Set topics["versions"] to reference output versions (now with populated metadata)
                if len(versions_keys) == 1:
                    corrected_meta_yml["topics"]["versions"] = corrected_meta_yml["output"][versions_keys[0]]
                    if hasattr(corrected_meta_yml["output"][versions_keys[0]], "yaml_set_anchor"):
                        corrected_meta_yml["output"][versions_keys[0]].yaml_set_anchor("versions")
                else:
                    corrected_meta_yml["topics"]["versions"] = []
                    for versions_key in versions_keys:
                        corrected_meta_yml["topics"]["versions"].append(corrected_meta_yml["output"][versions_key][0])
                        if hasattr(corrected_meta_yml["output"][versions_key], "yaml_set_anchor"):
                            corrected_meta_yml["output"][versions_key].yaml_set_anchor(versions_key)

        def _ensure_string_keys(obj):
            """Recursively ensure all dict keys are strings (e.g., convert 1.2 -> "1.2")"""
            if isinstance(obj, dict):
                return {str(k) if not isinstance(k, str) else k: _ensure_string_keys(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_ensure_string_keys(item) for item in obj]
            else:
                return obj

        corrected_meta_yml = _sort_meta_yml(corrected_meta_yml)
        corrected_meta_yml = _ensure_string_keys(corrected_meta_yml)

        with open(mod.meta_yml, "w") as fh:
            log.info(f"Updating {mod.meta_yml}")
            yaml.dump(corrected_meta_yml, fh)
            run_prettier_on_file(fh.name)
