#!/usr/bin/env python
"""
Lint the main.nf file of a module
"""

import re
import nf_core


def main_nf(module_lint_object, module):
    """
    Lint a single main.nf module file
    Can also be used to lint local module files,
    in which case failures should be interpreted
    as warnings
    """
    inputs = []
    outputs = []

    # Check whether file exists and load it
    try:
        with open(module.main_nf, "r") as fh:
            lines = fh.readlines()
        module.passed.append(("main_nf_exists", "Module file exists", module.main_nf))
    except FileNotFoundError as e:
        module.failed.append(("main_nf_exists", "Module file does not exist", module.main_nf))
        return

    # Check that options are defined
    initoptions_re = re.compile(r"\s*options\s*=\s*initOptions\s*\(\s*params\.options\s*\)\s*")
    paramsoptions_re = re.compile(r"\s*params\.options\s*=\s*\[:\]\s*")
    if any(initoptions_re.match(l) for l in lines) and any(paramsoptions_re.match(l) for l in lines):
        module.passed.append(("main_nf_options", "'options' variable specified", module.main_nf))
    else:
        module.warned.append(("main_nf_options", "'options' variable not specified", module.main_nf))

    # Go through module main.nf file and switch state according to current section
    # Perform section-specific linting
    state = "module"
    process_lines = []
    script_lines = []
    for l in lines:
        if re.search("^\s*process\s*\w*\s*{", l) and state == "module":
            state = "process"
        if re.search("input\s*:", l) and state == "process":
            state = "input"
            continue
        if re.search("output\s*:", l) and state == "input":
            state = "output"
            continue
        if re.search("script\s*:", l) and state == "output":
            state = "script"
            continue

        # Perform state-specific linting checks
        if state == "process" and not _is_empty(module, l):
            process_lines.append(l)
        if state == "input" and not _is_empty(module, l):
            inputs += _parse_input(module, l)
        if state == "output" and not _is_empty(module, l):
            outputs += _parse_output(module, l)
            outputs = list(set(outputs))  # remove duplicate 'meta's
        if state == "script" and not _is_empty(module, l):
            script_lines.append(l)

    # Check the process definitions
    if check_process_section(module, process_lines):
        module.passed.append(("main_nf_container", "Container versions match", module.main_nf))
    else:
        module.warned.append(("main_nf_container", "Container versions do not match", module.main_nf))

    # Check the script definition
    check_script_section(module, script_lines)

    # Check whether 'meta' is emitted when given as input
    if "meta" in inputs:
        module.has_meta = True
        if "meta" in outputs:
            module.passed.append(("main_nf_meta_output", "'meta' map emitted in output channel(s)", module.main_nf))
        else:
            module.failed.append(("main_nf_meta_output", "'meta' map not emitted in output channel(s)", module.main_nf))

        # if meta is specified, it should also be used as "saveAs ... meta:meta, publish_by_meta:['id']"
        save_as = [pl for pl in process_lines if "saveAs" in pl]
        if len(save_as) > 0 and re.search("\s*meta\s*:\s*meta", save_as[0]):
            module.passed.append(("main_nf_meta_saveas", "'meta:meta' specified in saveAs function", module.main_nf))
        else:
            module.failed.append(("main_nf_meta_saveas", "'meta:meta' unspecified in saveAs function", module.main_nf))

        if len(save_as) > 0 and re.search("\s*publish_by_meta\s*:\s*\['id'\]", save_as[0]):
            module.passed.append(
                (
                    "main_nf_publish_meta_saveas",
                    "'publish_by_meta:['id']' specified in saveAs function",
                    module.main_nf,
                )
            )
        else:
            module.failed.append(
                (
                    "main_nf_publish_meta_saveas",
                    "'publish_by_meta:['id']' unspecified in saveAs function",
                    module.main_nf,
                )
            )

    # Check that a software version is emitted
    if "version" in outputs:
        module.passed.append(("main_nf_version_emitted", "Module emits software version", module.main_nf))
    else:
        module.warned.append(("main_nf_version_emitted", "Module does not emit software version", module.main_nf))

    return inputs, outputs


def check_script_section(self, lines):
    """
    Lint the script section
    Checks whether 'def sotware' and 'def prefix' are defined
    """
    script = "".join(lines)

    # check for software
    if re.search("\s*def\s*software\s*=\s*getSoftwareName", script):
        self.passed.append(("main_nf_version_script", "Software version specified in script section", self.main_nf))
    else:
        self.warned.append(("main_nf_version_script", "Software version unspecified in script section", self.main_nf))

    # check for prefix (only if module has a meta map as input)
    if self.has_meta:
        if re.search("\s*prefix\s*=\s*options.suffix", script):
            self.passed.append(("main_nf_meta_prefix", "'prefix' specified in script section", self.main_nf))
        else:
            self.failed.append(("main_nf_meta_prefix", "'prefix' unspecified in script section", self.main_nf))


def check_process_section(self, lines):
    """
    Lint the section of a module between the process definition
    and the 'input:' definition
    Specifically checks for correct software versions
    and containers
    """
    # Checks that build numbers of bioconda, singularity and docker container are matching
    build_id = "build"
    singularity_tag = "singularity"
    docker_tag = "docker"
    bioconda_packages = []

    # Process name should be all capital letters
    self.process_name = lines[0].split()[1]
    if all([x.upper() for x in self.process_name]):
        self.passed.append(("process_capitals", "Process name is in capital letters", self.main_nf))
    else:
        self.failed.append(("process_capitals", "Process name is not in captial letters", self.main_nf))

    # Check that process labels are correct
    correct_process_labels = ["process_low", "process_medium", "process_high", "process_long"]
    process_label = [l for l in lines if "label" in l]
    if len(process_label) > 0:
        process_label = process_label[0].split()[1].strip().strip("'").strip('"')
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
        if re.search("bioconda::", l):
            bioconda_packages = [b for b in l.split() if "bioconda::" in b]
        if re.search("org/singularity", l):
            singularity_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()
        if re.search("biocontainers", l):
            docker_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()

    # Check that all bioconda packages have build numbers
    # Also check for newer versions
    for bp in bioconda_packages:
        bp = bp.strip("'").strip('"')
        # Check for correct version and newer versions
        try:
            bioconda_version = bp.split("=")[1]
            # response = _bioconda_package(bp)
            response = nf_core.utils.anaconda_package(bp)
        except LookupError as e:
            self.warned.append(("bioconda_version", "Conda version not specified correctly", self.main_nf))
        except ValueError as e:
            self.failed.append(("bioconda_version", "Conda version not specified correctly", self.main_nf))
        else:
            # Check that required version is available at all
            if bioconda_version not in response.get("versions"):
                self.failed.append(("bioconda_version", "Conda package had unknown version: `{}`", self.main_nf))
                continue  # No need to test for latest version, continue linting
            # Check version is latest available
            last_ver = response.get("latest_version")
            if last_ver is not None and last_ver != bioconda_version:
                package, ver = bp.split("=", 1)
                self.warned.append(
                    ("bioconda_latest", f"Conda update: {package} `{ver}` -> `{last_ver}`", self.main_nf)
                )
            else:
                self.passed.append(("bioconda_latest", "Conda package is the latest available: `{bp}`", self.main_nf))

    if docker_tag == singularity_tag:
        return True
    else:
        return False


def _parse_input(self, line):
    input = []
    # more than one input
    if "tuple" in line:
        line = line.replace("tuple", "")
        line = line.replace(" ", "")
        line = line.split(",")

        for elem in line:
            elem = elem.split("(")[1]
            elem = elem.replace(")", "").strip()
            input.append(elem)
    else:
        if "(" in line:
            input.append(line.split("(")[1].replace(")", ""))
        else:
            input.append(line.split()[1])
    return input


def _parse_output(self, line):
    output = []
    if "meta" in line:
        output.append("meta")
    if not "emit" in line:
        self.failed.append(("missing_emit", f"Missing emit statement: {line.strip()}", self.main_nf))
    if "emit" in line:
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
