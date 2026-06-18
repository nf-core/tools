"""
Lint the main.nf file of a module
"""

import logging
import re
from pathlib import Path

from rich.progress import Progress

from nf_core.components.components_differ import ComponentsDiffer
from nf_core.components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


def main_nf(
    module_lint_object, module: NFCoreComponent, fix_version: bool, registry: tuple[str, ...], progress_bar: Progress
) -> tuple[list[str], list[str]]:
    """Lint a ``main.nf`` module file

    Can also be used to lint local module files,
    in which case failures will be reported as warnings.

    The following checks are performed:

    * ``main_nf_module_granularity``: The module must represent a single command
      as ``<tool>`` or single subcommand with distinct functionality as
      ``<tool/subtool>``.

    * ``main_nf_exists``: The ``main.nf`` file must exist.

    * ``deprecated_dsl2``: The file must not contain deprecated DSL2 identifiers
      (``initOptions``, ``saveFiles``, ``getSoftwareName``, ``getProcessName``,
      ``publishDir``).

    * ``main_nf_script_outputs``: The process must have an ``output:`` block.

    * ``main_nf_container``: Container tags across the ``singularity``, ``docker``,
      and ``conda`` directives must reference the same software version. A warning
      is issued if they do not match.

    * ``main_nf_script_shell``: Exactly one of ``script:``, ``shell:``, or ``exec:``
      blocks must be present.

    * ``main_nf_shell_template``: If a ``shell:`` block is used, it must call
      a ``template``.

    * ``main_nf_meta_output``: If ``meta`` is present in the module inputs, it
      must also appear in at least one output channel.

    * ``main_nf_version_topic``: The module should emit software versions using
      a ``topic: versions`` output. A warning is issued if no such topic is found.

    * ``main_nf_version_emit``: The number of ``topic: versions`` outputs must
      equal the number of ``emit:`` outputs whose name starts with ``versions``.
      A warning is issued if a legacy YAML-based ``versions`` emit is used instead
      of a topic output.

    """

    inputs: list[str] = []
    emits: list[str] = []
    topics: list[str] = []

    # Check the module name
    check_nf_module_name(module, module.component_name)

    # Check if we have a patch file affecting the 'main.nf' file
    # otherwise read the lines directly from the module
    lines: list[str] = []
    if module.is_patched:
        lines = ComponentsDiffer.try_apply_patch(
            module.component_type,
            module.component_name,
            module_lint_object.modules_repo.repo_path,
            module.patch_path,
            Path(module.component_dir).relative_to(module.base_dir),
            reverse=True,
        ).get("main.nf", [""])

    if len(lines) == 0:
        try:
            # Check whether file exists and load it
            with open(module.main_nf) as fh:
                lines = fh.readlines()
            module.passed.append(("main_nf", "main_nf_exists", "Module file exists", module.main_nf))
        except FileNotFoundError as e:
            module.failed.append(("main_nf", "main_nf_exists", "Module file does not exist", module.main_nf))
            raise FileNotFoundError(f"Module file does not exist: {module.main_nf}") from e

    deprecated_i = ["initOptions", "saveFiles", "getSoftwareName", "getProcessName", "publishDir"]
    lines_j = "\n".join(lines) if len(lines) > 0 else ""

    for i in deprecated_i:
        if i in lines_j:
            module.failed.append(
                (
                    "main_nf",
                    "deprecated_dsl2",
                    f"`{i}` specified. No longer required for the latest nf-core/modules syntax!",
                    module.main_nf,
                )
            )
            break
    else:
        module.passed.append(("main_nf", "deprecated_dsl2", "No deprecated DSL2 syntax found", module.main_nf))

    # Go through module main.nf file and switch state according to current section
    # Perform section-specific linting
    state = "module"
    process_lines = []
    script_lines = []
    shell_lines = []
    exec_lines = []
    when_lines = []
    iter_lines = iter(lines)
    for line in iter_lines:
        if re.search(r"^\s*process\s*\w*\s*{", line) and state == "module":
            state = "process"
        if re.search(r"^\s*input\s*:", line) and state in ["process"]:
            state = "input"
            continue
        if re.search(r"^\s*output\s*:", line) and state in ["input", "process"]:
            state = "output"
            continue
        if re.search(r"^\s*when\s*:", line) and state in ["input", "output", "process"]:
            state = "when"
            continue
        if re.search(r"^\s*script\s*:", line) and state in ["input", "output", "when", "process"]:
            state = "script"
            continue
        if re.search(r"^\s*shell\s*:", line) and state in ["input", "output", "when", "process"]:
            state = "shell"
            continue
        if re.search(r"^\s*exec\s*:", line) and state in ["input", "output", "when", "process"]:
            state = "exec"
            continue

        # Perform state-specific linting checks
        if state == "process" and not _is_empty(line):
            process_lines.append(line)
        if state == "input" and not _is_empty(line):
            # allow multiline tuples
            if "tuple" in line and line.count("(") <= 1:
                joint_tuple = line
                while re.sub(r"\s", "", line) != ")":
                    joint_tuple = joint_tuple + line
                    line = next(iter_lines)
                line = joint_tuple
            inputs.extend(_parse_input(module, line))
        if state == "output" and not _is_empty(line):
            emits += _parse_output_emits(module, line)
            emits = list(set(emits))  # remove duplicate 'meta's
            topics += _parse_output_topics(module, line)
        if state == "when" and not _is_empty(line):
            when_lines.append(line)
        if state == "script" and not _is_empty(line):
            script_lines.append(line)
        if state == "shell" and not _is_empty(line):
            shell_lines.append(line)
        if state == "exec" and not _is_empty(line):
            exec_lines.append(line)

    # Check meta naming
    if inputs:
        check_meta_input_names(module, inputs)

    # Check that we have required sections
    if not len(emits):
        module.failed.append(("main_nf", "main_nf_script_outputs", "No process 'output' block found", module.main_nf))
    else:
        module.passed.append(("main_nf", "main_nf_script_outputs", "Process 'output' block found", module.main_nf))

    # Check the process definitions
    check_process_section(module, process_lines, registry, fix_version, progress_bar)

    # Check the when statement
    check_when_section(module, when_lines)

    # Check that we have script or shell, not both
    if sum(bool(block_lines) for block_lines in (script_lines, shell_lines, exec_lines)) > 1:
        module.failed.append(
            (
                "main_nf",
                "main_nf_script_shell",
                "Multiple script:/shell:/exec: blocks found, should use only one",
                module.main_nf,
            )
        )
    else:
        module.passed.append(
            ("main_nf", "main_nf_script_shell", "Only one script:/shell:/exec: block found", module.main_nf)
        )

    # Check the script definition
    if len(script_lines):
        check_script_section(module, script_lines)

    # Check that shell uses a template
    if len(shell_lines):
        if any("template" in line for line in shell_lines):
            module.passed.append(
                ("main_nf", "main_nf_shell_template", "`template` found in `shell` block", module.main_nf)
            )
        else:
            module.failed.append(
                ("main_nf", "main_nf_shell_template", "No `template` found in `shell` block", module.main_nf)
            )

    # Check whether 'meta' is emitted when given as input
    if inputs and "meta" in inputs:
        module.has_meta = True
        if emits:
            if "meta" in emits:
                module.passed.append(
                    (
                        "main_nf",
                        "main_nf_meta_output",
                        "'meta' map emitted in output channel(s)",
                        module.main_nf,
                    )
                )
            else:
                module.failed.append(
                    (
                        "main_nf",
                        "main_nf_meta_output",
                        "'meta' map not emitted in output channel(s)",
                        module.main_nf,
                    )
                )

    # Check that a software version is emitted
    if topics:
        if "versions" in topics:
            module.passed.append(
                ("main_nf", "main_nf_version_topic", "Module emits software versions as topic", module.main_nf)
            )
        else:
            module.failed.append(
                ("main_nf", "main_nf_version_topic", "Module does not emit software versions as topic", module.main_nf)
            )

    if emits:
        topic_versions_amount = sum(1 for t in topics if t == "versions")
        emit_versions_amount = sum(1 for e in emits if e.startswith("versions"))
        if topic_versions_amount == emit_versions_amount:
            module.passed.append(
                ("main_nf", "main_nf_version_emit", "Module emits each software version", module.main_nf)
            )
        elif "versions" in emits:
            module.warned.append(
                (
                    "main_nf",
                    "main_nf_version_emit",
                    "Module emits software versions YAML, please update this to topics output",
                    module.main_nf,
                )
            )
        else:
            module.failed.append(
                (
                    "main_nf",
                    "main_nf_version_emit",
                    "Module does not have an `emit:` and `topic:` for each software version",
                    module.main_nf,
                )
            )

    return inputs, emits


def check_nf_module_name(self, component_name):
    """
    Lint the module name
    Checks whether the module name has at most two levels of granularity, no
    punctuation and lowercase.
    """
    # Module name is lowercase
    if component_name.islower():
        self.passed.append(("main_nf", "main_nf_module_lowercase", "Process name is lowercase", self.main_nf))
    else:
        self.failed.append(("main_nf", "main_nf_module_lowercase", "Process name should be lowercase", self.main_nf))

    # Module name has no punctuation
    if component_name.replace("/", "").isalnum():
        self.passed.append(
            ("main_nf", "main_nf_module_no_punctuation", "Module properly named without punctuation", self.main_nf)
        )
    else:
        self.failed.append(
            ("main_nf", "main_nf_module_no_punctuation", "Module name should not have any punctuation", self.main_nf)
        )

    # Module name granularity
    if component_name.count("/") > 1:
        self.failed.append(
            ("main_nf", "main_nf_module_granularity", "Module not named as `<tool>` or `<tool/subtool>`", self.main_nf)
        )
    elif component_name.count("/") == 1:
        self.passed.append(
            ("main_nf", "main_nf_module_granularity", "Module properly named as `<tool/subtool>`", self.main_nf)
        )
    else:
        self.passed.append(("main_nf", "main_nf_module_granularity", "Module properly named as `<tool>`", self.main_nf))


def check_script_section(self, lines):
    """
    Lint the script section
    Checks whether `def prefix` is defined and whether getProcessName is used for `versions.yml`.
    """
    script = "".join(lines)

    # check for prefix (only if module has a meta map as input)
    if self.has_meta:
        if re.search(r"\s*prefix\s*=\s*task.ext.prefix", script):
            self.passed.append(
                (
                    "main_nf",
                    "main_nf_meta_prefix",
                    "'prefix' specified in script section",
                    self.main_nf,
                )
            )
        else:
            self.failed.append(
                (
                    "main_nf",
                    "main_nf_meta_prefix",
                    "'prefix' unspecified in script section",
                    self.main_nf,
                )
            )

    # Validate meta keys
    permitted_meta_keys = {"id", "single_end"}
    invalid_meta_keys = [
        f"{prefix}{key}"
        for prefix, key in re.findall(r"\b(meta\d*\??\.)(\w+)\b(?!\()", script)
        if key not in permitted_meta_keys
    ]
    if not invalid_meta_keys:
        self.passed.append(("main_nf", "main_nf_meta_key", "All 'meta' keys are valid", self.main_nf))
    else:
        self.failed.append(
            (
                "main_nf",
                "main_nf_meta_key",
                f"Invalid 'meta' keys detected: {', '.join(invalid_meta_keys)}",
                self.main_nf,
            )
        )

    # Validate ext keys
    permitted_ext_keys = {"ext.args", "ext.prefix", "ext.prefix2", "ext.use_gpu"}
    invalid_ext_keys = [
        key
        for key in re.findall(r"\bext\.\w+", script)
        if key not in permitted_ext_keys and not re.match(r"^ext\.args([2-9]|\d{2,})$", key)
    ]
    if not invalid_ext_keys:
        self.passed.append(("main_nf", "main_nf_ext_key", "All 'ext' keys are valid", self.main_nf))
    else:
        self.failed.append(
            (
                "main_nf",
                "main_nf_ext_key",
                f"Invalid 'ext' keys detected: {', '.join(invalid_ext_keys)}",
                self.main_nf,
            )
        )


def check_when_section(self, lines):
    """
    Lint the when: section
    Checks whether the line is modified from 'task.ext.when == null || task.ext.when'
    """
    if len(lines) == 0:
        self.failed.append(("main_nf", "when_exist", "when: condition has been removed", self.main_nf))
        return
    if len(lines) > 1:
        self.failed.append(("main_nf", "when_exist", "when: condition has too many lines", self.main_nf))
        return
    self.passed.append(("main_nf", "when_exist", "when: condition is present", self.main_nf))

    # Check the condition hasn't been changed.
    if lines[0].strip() != "task.ext.when == null || task.ext.when":
        self.failed.append(("main_nf", "when_condition", "when: condition has been altered", self.main_nf))
        return
    self.passed.append(("main_nf", "when_condition", "when: condition is unchanged", self.main_nf))


def check_process_section(
    self, lines: list[str], registry: tuple[str, ...], fix_version: bool, progress_bar: Progress | None
):
    """Lint the section of a module between the process definition
    and the 'input:' definition
    Specifically checks for correct software versions
    and containers

    Args:
        lines (list[str]): Content of process.
        registry (tuple[str, ...]): Allowed container registry prefixes.
        fix_version (bool): Fix software version
        progress_bar (ProgressBar): Progress bar to update.

    Returns:
        None
    """
    # Check that we have a process section
    if len(lines) == 0:
        self.failed.append(("main_nf", "process_exist", "Process definition does not exist", self.main_nf))
        return
    self.passed.append(("main_nf", "process_exist", "Process definition exists", self.main_nf))

    # Check that the process name is correctly formated from the component name
    check_process_name_format(self, self.process_name, self.component_name)

    # Check that process labels are correct
    check_process_labels(self, lines)

    # Deprecated enable_conda
    for _i, raw_line in enumerate(lines):
        line = raw_line.strip(" \n'\"}:?")

        # Catch preceding "container "
        if line.startswith("container"):
            line = line.replace("container", "").strip(" \n'\"}:?")

        if _container_type(line) == "conda":
            match = re.search(r"params\.enable_conda", line)
            if match is None:
                self.passed.append(
                    (
                        "main_nf",
                        "deprecated_enable_conda",
                        "Deprecated parameter 'params.enable_conda' correctly not found in the conda definition",
                        self.main_nf,
                    )
                )
            else:
                self.failed.append(
                    (
                        "main_nf",
                        "deprecated_enable_conda",
                        "Found deprecated parameter 'params.enable_conda' in the conda definition",
                        self.main_nf,
                    )
                )
        if _container_type(line) == "singularity":
            self.warned.append(
                (
                    "main_nf",
                    "deprecated_container_syntax",
                    f"Singularity container URL syntax is deprecated. Please migrate to seqera containers using `nf-core modules container create {self.component_name}`.",
                    self.main_nf,
                )
            )

        if line.startswith("container") or _container_type(line) == "docker" or _container_type(line) == "singularity":
            check_container_link_line(self, raw_line, registry)


def check_process_name_format(self, process_name, component_name):
    """
    Lint the process name
    Checks that the process name in the module file is uppercase and derived
    from the software and tool name separated by an underscore.
    """
    # Process name should be all capital letters
    if process_name.isupper():
        self.passed.append(("main_nf", "process_capitals", "Process name is in capital letters", self.main_nf))
    else:
        self.failed.append(("main_nf", "process_capitals", "Process name is not in capital letters", self.main_nf))

    # Process name should be made from the module name
    if component_name.upper().replace("/", "_") == process_name:
        self.passed.append(("main_nf", "module_process_name", "Process name is derived from module name", self.main_nf))
    else:
        self.failed.append(
            ("main_nf", "module_process_name", "Process name is not derived from module name", self.main_nf)
        )


def check_process_labels(self, lines):
    correct_process_labels = [
        "process_single",
        "process_low",
        "process_medium",
        "process_high",
        "process_long",
        "process_low_memory",
        "process_high_memory",
    ]
    all_labels = [line.strip() for line in lines if line.lstrip().startswith("label ")]
    bad_labels = []
    good_labels = []
    if len(all_labels) > 0:
        for label in all_labels:
            try:
                label = re.match(r"^label\s+'?\"?([a-zA-Z0-9_-]+)'?\"?$", label).group(1)
            except AttributeError:
                self.warned.append(
                    (
                        "main_nf",
                        "process_standard_label",
                        f"Specified label appears to contain non-alphanumerics: {label}",
                        self.main_nf,
                    )
                )
                continue
            if label not in correct_process_labels:
                bad_labels.append(label)
            else:
                good_labels.append(label)
        if len(good_labels) > 1:
            self.warned.append(
                (
                    "main_nf",
                    "process_standard_label",
                    f"Conflicting process labels found: `{'`,`'.join(good_labels)}`",
                    self.main_nf,
                )
            )
        elif len(good_labels) == 1:
            self.passed.append(("main_nf", "process_standard_label", "Correct process label", self.main_nf))
        else:
            self.warned.append(("main_nf", "process_standard_label", "Standard process label not found", self.main_nf))
        if len(bad_labels) > 0:
            self.warned.append(
                (
                    "main_nf",
                    "process_standard_label",
                    f"Non-standard labels found: `{'`,`'.join(bad_labels)}`",
                    self.main_nf,
                )
            )
        if len(all_labels) > len(set(all_labels)):
            self.warned.append(
                (
                    "main_nf",
                    "process_standard_label",
                    f"Duplicate labels found: `{'`,`'.join(sorted(all_labels))}`",
                    self.main_nf,
                )
            )
    else:
        self.warned.append(("main_nf", "process_standard_label", "Process label not specified", self.main_nf))


def check_container_link_line(self, raw_line, registry):
    """Look for common problems in the container name / URL, for docker and singularity."""

    line = raw_line.strip(" \n'\"}:?")

    # lint double quotes
    if line.count('"') > 2:
        self.failed.append(
            (
                "main_nf",
                "container_links",
                f"Too many double quotes found when specifying container: {line.removeprefix('container ')}",
                self.main_nf,
            )
        )
    else:
        self.passed.append(
            (
                "main_nf",
                "container_links",
                f"Correct number of double quotes found when specifying container: {line.removeprefix('container ')}",
                self.main_nf,
            )
        )

    # Check for spaces in url
    single_quoted_items = raw_line.split("'")
    double_quoted_items = raw_line.split('"')
    # Look for container link as single item surrounded by quotes
    # (if there are multiple links, this will be warned in the next check)
    container_link = None
    if len(single_quoted_items) == 3 or len(single_quoted_items) == 5 and " in [" in raw_line:
        container_link = single_quoted_items[1]
    elif len(double_quoted_items) == 3:
        container_link = double_quoted_items[1]
    if container_link:
        if " " in container_link:
            self.failed.append(
                (
                    "main_nf",
                    "container_links",
                    f"Space character found in container: '{container_link}'",
                    self.main_nf,
                )
            )
        else:
            self.passed.append(
                (
                    "main_nf",
                    "container_links",
                    f"No space characters found in container: '{container_link}'",
                    self.main_nf,
                )
            )

        # Check container registry prefix
        if container_link.startswith(registry):
            self.passed.append(
                (
                    "main_nf",
                    "container_links",
                    f"Container prefix is correct: {container_link}",
                    self.main_nf,
                )
            )
        else:
            self.failed.append(
                (
                    "main_nf",
                    "container_links",
                    f"Container prefix is not correct. Please add one of the allowed registry prefixes: {', '.join(registry)}",
                    self.main_nf,
                )
            )

        # lint more than one container in the same line
        if ("https://containers" in line or "https://depot" in line) and (
            "biocontainers/" in line or line.startswith(registry)
        ):
            self.warned.append(
                (
                    "main_nf",
                    "container_links",
                    "Docker and Singularity containers specified in the same line. Only first one checked.",
                    self.main_nf,
                )
            )


def check_meta_input_names(self, inputs):
    """
    Check ``meta_input_names``: The  meta* variable names must follow the pattern `meta`, `meta2`, `meta3`, etc.
    Args:
        inputs (list): List of input variable names
    """

    meta_vars = [var for var in inputs if var.startswith("meta")]

    if not meta_vars:
        return  # No meta variables to check

    # Expected pattern: 'meta' or 'meta' followed by a number (meta2, meta3, etc.)
    valid_pattern = re.compile(r"^meta(\d+)?$")

    invalid_meta_vars = []
    valid_numbers = []

    for var in meta_vars:
        if not valid_pattern.match(var):
            invalid_meta_vars.append(var)
        else:
            # Extract number if present
            match = re.match(r"^meta(\d+)?$", var)
            if match.group(1):  # Has a number
                number_str = match.group(1)
                number_int = int(number_str)

                if number_str != str(number_int) or number_int < 2:
                    # Check for leading zeros (e.g., meta02, meta003) or meta0 and meta1
                    invalid_meta_vars.append(var)
                else:
                    valid_numbers.append(number_int)

    # Check for invalid names
    if invalid_meta_vars:
        self.failed.append(
            (
                "main_nf",
                "meta_input_names",
                f"Meta variables must be named 'meta', 'meta2', 'meta3', etc. Found: {', '.join(invalid_meta_vars)}",
                self.main_nf,
            )
        )

    # Check for proper sequencing (2, 3, 4... not 2, 5, 3)
    if valid_numbers:
        expected = list(range(2, len(valid_numbers) + 2))
        if valid_numbers != expected:
            self.warned.append(
                (
                    "main_nf",
                    "meta_input_names",
                    f"Meta variable numbers should be sequential starting at 2. Found: meta{', meta'.join(map(str, valid_numbers))}",
                    self.main_nf,
                )
            )

    if not invalid_meta_vars and (not valid_numbers or valid_numbers == list(range(2, len(valid_numbers) + 2))):
        self.passed.append(
            (
                "main_nf",
                "meta_input_names",
                f"Meta variable names follow correct pattern: {', '.join(sorted(meta_vars))}",
                self.main_nf,
            )
        )


def _parse_input(self, line_raw):
    """
    Return list of input channel names from an input line.

    If more than one elements in channel should work with both of:
        tuple val(meta), path(reads)
        tuple val(meta), path(reads, stageAs: "input*/*")

    If using a tuple, channel names must be in (parentheses)
    """
    inputs = []
    # Remove comments and trailing whitespace
    line = line_raw.split("//")[0]
    line = line.strip()
    # Tuples with multiple elements
    if "tuple" in line:
        matches = re.findall(r"\((\w+)\)", line)
        if matches:
            inputs.extend(matches)
            self.passed.append(
                (
                    "main_nf",
                    "main_nf_input_tuple",
                    f"Channel names for tuple found: `{line}`",
                    self.main_nf,
                )
            )
        else:
            self.failed.append(
                (
                    "main_nf",
                    "main_nf_input_tuple",
                    f"Found tuple but no channel names: `{line}`",
                    self.main_nf,
                )
            )
    # Single element inputs
    else:
        if "(" in line:
            match = re.search(r"\((\w+)\)", line)
            if match:
                inputs.append(match.group(1))
        else:
            inputs.append(line.split()[1])
    return inputs


def _parse_output_emits(self, line: str) -> list[str]:
    output = []
    if "meta" in line:
        output.append("meta")
    emit_regex = re.search(r"^.*emit:\s*([^,\s]*)", line)
    if not emit_regex:
        self.failed.append(("missing_emit", f"Missing emit statement: {line.strip()}", self.main_nf))
    else:
        output.append(emit_regex.group(1).strip())
    return output


def _parse_output_topics(self, line: str) -> list[str]:
    output = []
    if "meta" in line:
        output.append("meta")
    topic_regex = re.search(r"^.*topic:\s*([^,\s]*)", line)
    if topic_regex:
        topic_name = topic_regex.group(1).strip()
        output.append(topic_name)
        if topic_name == "versions":
            if re.search(
                r'tuple\s+val\("\${\s*task\.process\s*}"\)\s*,\s*val\(.*\)\s*,\s*(?:eval|val)\(.*\)', line
            ) or re.search(r"path\s*\(?\"versions\.yml\"\)?", line):
                self.passed.append(
                    (
                        "main_nf",
                        "wrong_version_output",
                        "Versions topic output is correctly formatted",
                        self.main_nf,
                    )
                )

            else:
                self.failed.append(
                    (
                        "main_nf",
                        "wrong_version_output",
                        "Versions topic output is not correctly formatted, expected `tuple val(\"${task.process}\"), val('<tool>'), eval(\"<version_command>\")|val('<version>')`` or `path version.yml` if using a template script.",
                        self.main_nf,
                    )
                )

            if re.search(r"emit:\s*versions_[\d\w]+", line):
                self.passed.append(
                    (
                        "main_nf",
                        "wrong_version_emit",
                        "Version emit is correctly formatted",
                        self.main_nf,
                    )
                )
            else:
                if re.search(r"path\s*\(?\"versions\.yml\"\)?", line):
                    if re.search(r"emit:\s*versions\b", line):
                        self.passed.append(
                            (
                                "main_nf",
                                "wrong_version_yml_emit",
                                "Version emit is correctly formatted",
                                self.main_nf,
                            )
                        )
                    else:
                        self.failed.append(
                            (
                                "main_nf",
                                "wrong_versions_yml_emit",
                                "Version emit should be `versions`",
                                self.main_nf,
                            )
                        )
                else:
                    self.failed.append(
                        (
                            "main_nf",
                            "wrong_version_emit",
                            "Version emit should follow the format `versions_<tool_or_package>`, e.g.: `versions_samtools`, `versions_gatk4`",
                            self.main_nf,
                        )
                    )

    return output


def _is_empty(line):
    """Check whether a line is empty or a comment"""
    empty = False
    if line.strip().startswith("//"):
        empty = True
    if line.strip().replace(" ", "") == "":
        empty = True
    return empty


def _container_type(line):
    """Returns the container type of a build."""
    if line.startswith("conda"):
        return "conda"
    if line.startswith("https://"):
        # Look for a http download URL.
        # Thanks Stack Overflow for the regex: https://stackoverflow.com/a/3809435/713980
        url_regex = (
            r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        )
        url_match = re.search(url_regex, line, re.S)
        if url_match:
            return "singularity"
        return None
    if line.count("/") >= 1 and line.count(":") == 1 and line.count(" ") == 0 and "https://" not in line:
        return "docker"
