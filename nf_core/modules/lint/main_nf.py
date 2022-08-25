#!/usr/bin/env python
"""
Lint the main.nf file of a module
"""

import logging
import re
import sqlite3
from pathlib import Path

import requests

import nf_core
import nf_core.modules.module_utils
from nf_core.modules.modules_differ import ModulesDiffer

log = logging.getLogger(__name__)


def main_nf(module_lint_object, module, fix_version, progress_bar):
    """
    Lint a ``main.nf`` module file

    Can also be used to lint local module files,
    in which case failures will be reported as
    warnings.

    The test checks for the following:

    * Software versions and containers are valid
    * The module has a process label and it is among
      the standard ones.
    * If a ``meta`` map is defined as one of the modules
      inputs it should be defined as one of the outputs,
      and be correctly configured in the ``saveAs`` function.
    * The module script section should contain definitions
      of ``software`` and ``prefix``
    """

    inputs = []
    outputs = []

    # Check if we have a patch file affecting the 'main.nf' file
    # otherwise read the lines directly from the module
    lines = None
    if module.is_patched:
        lines = ModulesDiffer.try_apply_patch(
            module.module_name,
            module_lint_object.modules_repo.fullname,
            module.patch_path,
            Path(module.module_dir).relative_to(module.base_dir),
            reverse=True,
        ).get("main.nf")
    if lines is None:
        try:
            # Check whether file exists and load it
            with open(module.main_nf, "r") as fh:
                lines = fh.readlines()
            module.passed.append(("main_nf_exists", "Module file exists", module.main_nf))
        except FileNotFoundError:
            module.failed.append(("main_nf_exists", "Module file does not exist", module.main_nf))
            return

    deprecated_i = ["initOptions", "saveFiles", "getSoftwareName", "getProcessName", "publishDir"]
    lines_j = "\n".join(lines)
    for i in deprecated_i:
        if i in lines_j:
            module.failed.append(
                (
                    "deprecated_dsl2",
                    f"`{i}` specified. No longer required for the latest nf-core/modules syntax!",
                    module.main_nf,
                )
            )

    # Go through module main.nf file and switch state according to current section
    # Perform section-specific linting
    state = "module"
    process_lines = []
    script_lines = []
    shell_lines = []
    when_lines = []
    for l in lines:
        if re.search(r"^\s*process\s*\w*\s*{", l) and state == "module":
            state = "process"
        if re.search(r"input\s*:", l) and state in ["process"]:
            state = "input"
            continue
        if re.search(r"output\s*:", l) and state in ["input", "process"]:
            state = "output"
            continue
        if re.search(r"when\s*:", l) and state in ["input", "output", "process"]:
            state = "when"
            continue
        if re.search(r"script\s*:", l) and state in ["input", "output", "when", "process"]:
            state = "script"
            continue
        if re.search(r"shell\s*:", l) and state in ["input", "output", "when", "process"]:
            state = "shell"
            continue

        # Perform state-specific linting checks
        if state == "process" and not _is_empty(module, l):
            process_lines.append(l)
        if state == "input" and not _is_empty(module, l):
            inputs.extend(_parse_input(module, l))
        if state == "output" and not _is_empty(module, l):
            outputs += _parse_output(module, l)
            outputs = list(set(outputs))  # remove duplicate 'meta's
        if state == "when" and not _is_empty(module, l):
            when_lines.append(l)
        if state == "script" and not _is_empty(module, l):
            script_lines.append(l)
        if state == "shell" and not _is_empty(module, l):
            shell_lines.append(l)

    # Check that we have required sections
    if not len(outputs):
        module.failed.append(("main_nf_script_outputs", "No process 'output' block found", module.main_nf))
    else:
        module.passed.append(("main_nf_script_outputs", "Process 'output' block found", module.main_nf))

    # Check the process definitions
    if check_process_section(module, process_lines, fix_version, progress_bar):
        module.passed.append(("main_nf_container", "Container versions match", module.main_nf))
    else:
        module.warned.append(("main_nf_container", "Container versions do not match", module.main_nf))

    # Check the when statement
    check_when_section(module, when_lines)

    # Check that we have script or shell, not both
    if len(script_lines) and len(shell_lines):
        module.failed.append(("main_nf_script_shell", "Script and Shell found, should use only one", module.main_nf))

    # Check the script definition
    if len(script_lines):
        check_script_section(module, script_lines)

    # Check that shell uses a template
    if len(shell_lines):
        if any("template" in l for l in shell_lines):
            module.passed.append(("main_nf_shell_template", "`template` found in `shell` block", module.main_nf))
        else:
            module.failed.append(("main_nf_shell_template", "No `template` found in `shell` block", module.main_nf))

    # Check whether 'meta' is emitted when given as input
    if inputs:
        if "meta" in inputs:
            module.has_meta = True
            if outputs:
                if "meta" in outputs:
                    module.passed.append(
                        ("main_nf_meta_output", "'meta' map emitted in output channel(s)", module.main_nf)
                    )
                else:
                    module.failed.append(
                        ("main_nf_meta_output", "'meta' map not emitted in output channel(s)", module.main_nf)
                    )

    # Check that a software version is emitted
    if outputs:
        if "versions" in outputs:
            module.passed.append(("main_nf_version_emitted", "Module emits software version", module.main_nf))
        else:
            module.warned.append(("main_nf_version_emitted", "Module does not emit software version", module.main_nf))

    return inputs, outputs


def check_script_section(self, lines):
    """
    Lint the script section
    Checks whether `def prefix` is defined and whether getProcessName is used for `versions.yml`.
    """
    script = "".join(lines)

    # check that process name is used for `versions.yml`
    if re.search(r"\$\{\s*task\.process\s*\}", script):
        self.passed.append(("main_nf_version_script", "Process name used for versions.yml", self.main_nf))
    else:
        self.warned.append(("main_nf_version_script", "Process name not used for versions.yml", self.main_nf))

    # check for prefix (only if module has a meta map as input)
    if self.has_meta:
        if re.search(r"\s*prefix\s*=\s*task.ext.prefix", script):
            self.passed.append(("main_nf_meta_prefix", "'prefix' specified in script section", self.main_nf))
        else:
            self.failed.append(("main_nf_meta_prefix", "'prefix' unspecified in script section", self.main_nf))


def check_when_section(self, lines):
    """
    Lint the when: section
    Checks whether the line is modified from 'task.ext.when == null || task.ext.when'
    """
    if len(lines) == 0:
        self.failed.append(("when_exist", "when: condition has been removed", self.main_nf))
        return
    if len(lines) > 1:
        self.failed.append(("when_exist", "when: condition has too many lines", self.main_nf))
        return
    self.passed.append(("when_exist", "when: condition is present", self.main_nf))

    # Check the condition hasn't been changed.
    if lines[0].strip() != "task.ext.when == null || task.ext.when":
        self.failed.append(("when_condition", "when: condition has been altered", self.main_nf))
        return
    self.passed.append(("when_condition", "when: condition is unchanged", self.main_nf))


def check_process_section(self, lines, fix_version, progress_bar):
    """
    Lint the section of a module between the process definition
    and the 'input:' definition
    Specifically checks for correct software versions
    and containers
    """
    # Check that we have a process section
    if len(lines) == 0:
        self.failed.append(("process_exist", "Process definition does not exist", self.main_nf))
        return
    self.passed.append(("process_exist", "Process definition exists", self.main_nf))

    # Checks that build numbers of bioconda, singularity and docker container are matching
    singularity_tag = "singularity"
    docker_tag = "docker"
    bioconda_packages = []

    # Process name should be all capital letters
    self.process_name = lines[0].split()[1]
    if all(x.upper() for x in self.process_name):
        self.passed.append(("process_capitals", "Process name is in capital letters", self.main_nf))
    else:
        self.failed.append(("process_capitals", "Process name is not in capital letters", self.main_nf))

    # Check that process labels are correct
    correct_process_labels = ["process_low", "process_medium", "process_high", "process_long"]
    process_label = [l for l in lines if l.lstrip().startswith("label")]
    if len(process_label) > 0:
        try:
            process_label = re.search("process_[A-Za-z]+", process_label[0]).group(0)
        except AttributeError:
            process_label = re.search("'([A-Za-z_-]+)'", process_label[0]).group(0)
        finally:
            if not process_label in correct_process_labels:
                self.warned.append(
                    (
                        "process_standard_label",
                        f"Process label ({process_label}) is not among standard labels: `{'`,`'.join(correct_process_labels)}`",
                        self.main_nf,
                    )
                )
            else:
                self.passed.append(("process_standard_label", "Correct process label", self.main_nf))
    else:
        self.warned.append(("process_standard_label", "Process label unspecified", self.main_nf))
    for l in lines:
        if _container_type(l) == "bioconda":
            bioconda_packages = [b for b in l.split() if "bioconda::" in b]
        l = l.strip(" '\"")
        if _container_type(l) == "singularity":
            # e.g. "https://containers.biocontainers.pro/s3/SingImgsRepo/biocontainers/v1.2.0_cv1/biocontainers_v1.2.0_cv1.img' :" -> v1.2.0_cv1
            # e.g. "https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0' :" -> 0.11.9--0
            match = re.search(r"(?:/)?(?:biocontainers_)?(?::)?([A-Za-z\d\-_.]+?)(?:\.img)?['\"]", l)
            if match is not None:
                singularity_tag = match.group(1)
                self.passed.append(("singularity_tag", f"Found singularity tag: {singularity_tag}", self.main_nf))
            else:
                self.failed.append(("singularity_tag", "Unable to parse singularity tag", self.main_nf))
                singularity_tag = None
        if _container_type(l) == "docker":
            # e.g. "quay.io/biocontainers/krona:2.7.1--pl526_5' }" -> 2.7.1--pl526_5
            # e.g. "biocontainers/biocontainers:v1.2.0_cv1' }" -> v1.2.0_cv1
            match = re.search(r"(?:[/])?(?::)?([A-Za-z\d\-_.]+)['\"]", l)
            if match is not None:
                docker_tag = match.group(1)
                self.passed.append(("docker_tag", f"Found docker tag: {docker_tag}", self.main_nf))
            else:
                self.failed.append(("docker_tag", "Unable to parse docker tag", self.main_nf))
                docker_tag = None

    # Check that all bioconda packages have build numbers
    # Also check for newer versions
    for bp in bioconda_packages:
        bp = bp.strip("'").strip('"')
        # Check for correct version and newer versions
        try:
            bioconda_version = bp.split("=")[1]
            # response = _bioconda_package(bp)
            response = nf_core.utils.anaconda_package(bp)
        except LookupError:
            self.warned.append(("bioconda_version", "Conda version not specified correctly", self.main_nf))
        except ValueError:
            self.failed.append(("bioconda_version", "Conda version not specified correctly", self.main_nf))
        else:
            # Check that required version is available at all
            if bioconda_version not in response.get("versions"):
                self.failed.append(
                    ("bioconda_version", f"Conda package had unknown version: `{bioconda_version}`", self.main_nf)
                )
                continue  # No need to test for latest version, continue linting
            # Check version is latest available
            last_ver = response.get("latest_version")
            if last_ver is not None and last_ver != bioconda_version:
                package, ver = bp.split("=", 1)
                # If a new version is available and fix is True, update the version
                if fix_version:
                    try:
                        fixed = _fix_module_version(self, bioconda_version, last_ver, singularity_tag, response)
                    except FileNotFoundError as e:
                        fixed = False
                        log.debug(f"Unable to update package {package} due to error: {e}")
                    else:
                        if fixed:
                            progress_bar.print(f"[blue]INFO[/blue]\t Updating package '{package}' {ver} -> {last_ver}")
                            log.debug(f"Updating package {package} {ver} -> {last_ver}")
                            self.passed.append(
                                (
                                    "bioconda_latest",
                                    f"Conda package has been updated to the latest available: `{bp}`",
                                    self.main_nf,
                                )
                            )
                        else:
                            progress_bar.print(
                                f"[blue]INFO[/blue]\t Tried to update package. Unable to update package '{package}' {ver} -> {last_ver}"
                            )
                            log.debug(f"Unable to update package {package} {ver} -> {last_ver}")
                            self.warned.append(
                                ("bioconda_latest", f"Conda update: {package} `{ver}` -> `{last_ver}`", self.main_nf)
                            )
                # Add available update as a warning
                else:
                    self.warned.append(
                        ("bioconda_latest", f"Conda update: {package} `{ver}` -> `{last_ver}`", self.main_nf)
                    )
            else:
                self.passed.append(("bioconda_latest", f"Conda package is the latest available: `{bp}`", self.main_nf))

    return docker_tag == singularity_tag


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
        else:
            self.failed.append(
                (
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


def _parse_output(self, line):
    output = []
    if "meta" in line:
        output.append("meta")
    if not "emit:" in line:
        self.failed.append(("missing_emit", f"Missing emit statement: {line.strip()}", self.main_nf))
    else:
        output.append(line.split("emit:")[1].strip())

    return output


def _is_empty(self, line):
    """Check whether a line is empty or a comment"""
    empty = False
    if line.strip().startswith("//"):
        empty = True
    if line.strip().replace(" ", "") == "":
        empty = True
    return empty


def _fix_module_version(self, current_version, latest_version, singularity_tag, response):
    """Updates the module version

    Changes the bioconda current version by the latest version.
    Obtains the latest build from bioconda response
    Checks that the new URLs for docker and singularity with the tag [version]--[build] are valid
    Changes the docker and singularity URLs
    """
    # Get latest build
    build = _get_build(response)

    with open(self.main_nf, "r") as source:
        lines = source.readlines()

    # Check if the new version + build exist and replace
    new_lines = []
    for line in lines:
        l = line.strip(" '\"")
        build_type = _container_type(l)
        if build_type == "bioconda":
            new_lines.append(re.sub(rf"{current_version}", f"{latest_version}", line))
        elif build_type == "singularity" or build_type == "docker":
            # Check that the new url is valid
            new_url = re.search(
                "(?:['\"])(.+)(?:['\"])", re.sub(rf"{singularity_tag}", f"{latest_version}--{build}", line)
            ).group(1)
            try:
                response_new_container = requests.get(
                    "https://" + new_url if not new_url.startswith("https://") else new_url, stream=True
                )
                log.debug(
                    f"Connected to URL: {'https://' + new_url if not new_url.startswith('https://') else new_url}, status_code: {response_new_container.status_code}"
                )
            except (requests.exceptions.RequestException, sqlite3.InterfaceError) as e:
                log.debug(f"Unable to connect to url '{new_url}' due to error: {e}")
                return False
            if response_new_container.status_code != 200:
                return False
            new_lines.append(re.sub(rf"{singularity_tag}", f"{latest_version}--{build}", line))
        else:
            new_lines.append(line)

    # Replace outdated versions by the latest one
    with open(self.main_nf, "w") as source:
        for line in new_lines:
            source.write(line)

    return True


def _get_build(response):
    """Get the latest build of the container version"""
    build_times = []
    latest_v = response.get("latest_version")
    files = response.get("files")
    for f in files:
        if f.get("version") == latest_v:
            build_times.append((f.get("upload_time"), f.get("attrs").get("build")))
    return sorted(build_times, key=lambda tup: tup[0], reverse=True)[0][1]


def _container_type(line):
    """Returns the container type of a build."""
    if re.search("bioconda::", line):
        return "bioconda"
    if line.startswith("https://containers") or line.startswith("https://depot"):
        # Look for a http download URL.
        # Thanks Stack Overflow for the regex: https://stackoverflow.com/a/3809435/713980
        url_regex = (
            r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
        )
        url_match = re.search(url_regex, line, re.S)
        if url_match:
            return "singularity"
        return None
    if line.startswith("biocontainers/") or line.startswith("quay.io/"):
        return "docker"
