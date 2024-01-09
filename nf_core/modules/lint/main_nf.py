"""
Lint the main.nf file of a module
"""

import logging
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests
import yaml

import nf_core
import nf_core.modules.modules_utils
from nf_core.modules.modules_differ import ModulesDiffer

log = logging.getLogger(__name__)


def main_nf(module_lint_object, module, fix_version, registry, progress_bar):
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
            module.component_name,
            module_lint_object.modules_repo.repo_path,
            module.patch_path,
            Path(module.component_dir).relative_to(module.base_dir),
            reverse=True,
        ).get("main.nf")
    if lines is None:
        try:
            # Check whether file exists and load it
            with open(module.main_nf) as fh:
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
    for line in lines:
        if re.search(r"^\s*process\s*\w*\s*{", line) and state == "module":
            state = "process"
        if re.search(r"input\s*:", line) and state in ["process"]:
            state = "input"
            continue
        if re.search(r"output\s*:", line) and state in ["input", "process"]:
            state = "output"
            continue
        if re.search(r"when\s*:", line) and state in ["input", "output", "process"]:
            state = "when"
            continue
        if re.search(r"script\s*:", line) and state in ["input", "output", "when", "process"]:
            state = "script"
            continue
        if re.search(r"shell\s*:", line) and state in ["input", "output", "when", "process"]:
            state = "shell"
            continue

        # Perform state-specific linting checks
        if state == "process" and not _is_empty(line):
            process_lines.append(line)
        if state == "input" and not _is_empty(line):
            inputs.extend(_parse_input(module, line))
        if state == "output" and not _is_empty(line):
            outputs += _parse_output(module, line)
            outputs = list(set(outputs))  # remove duplicate 'meta's
        if state == "when" and not _is_empty(line):
            when_lines.append(line)
        if state == "script" and not _is_empty(line):
            script_lines.append(line)
        if state == "shell" and not _is_empty(line):
            shell_lines.append(line)

    # Check that we have required sections
    if not len(outputs):
        module.failed.append(("main_nf_script_outputs", "No process 'output' block found", module.main_nf))
    else:
        module.passed.append(("main_nf_script_outputs", "Process 'output' block found", module.main_nf))

    # Check the process definitions
    if check_process_section(module, process_lines, registry, fix_version, progress_bar):
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
        if any("template" in line for line in shell_lines):
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


def check_process_section(self, lines, registry, fix_version, progress_bar):
    """Lint the section of a module between the process definition
    and the 'input:' definition
    Specifically checks for correct software versions
    and containers

    Args:
        lines (List[str]): Content of process.
        registry (str): Base Docker registry for containers. Typically quay.io.
        fix_version (bool): Fix software version
        progress_bar (ProgressBar): Progress bar to update.

    Returns:
        Optional[bool]: True if singularity and docker containers match, False otherwise. If process definition does not exist, None.
    """
    # Check that we have a process section
    if len(lines) == 0:
        self.failed.append(("process_exist", "Process definition does not exist", self.main_nf))
        return
    self.passed.append(("process_exist", "Process definition exists", self.main_nf))

    # Checks that build numbers of bioconda, singularity and docker container are matching
    singularity_tag = None
    docker_tag = None
    bioconda_packages = []

    # Process name should be all capital letters
    self.process_name = lines[0].split()[1]
    if all(x.upper() for x in self.process_name):
        self.passed.append(("process_capitals", "Process name is in capital letters", self.main_nf))
    else:
        self.failed.append(("process_capitals", "Process name is not in capital letters", self.main_nf))

    # Check that process labels are correct
    check_process_labels(self, lines)

    # Deprecated enable_conda
    for i, raw_line in enumerate(lines):
        url = None
        line = raw_line.strip(" \n'\"}:")

        # Catch preceeding "container "
        if line.startswith("container"):
            line = line.replace("container", "").strip(" \n'\"}:")

        if _container_type(line) == "conda":
            if "bioconda::" in line:
                bioconda_packages = [b for b in line.split() if "bioconda::" in b]
            match = re.search(r"params\.enable_conda", line)
            if match is None:
                self.passed.append(
                    (
                        "deprecated_enable_conda",
                        "Deprecated parameter 'params.enable_conda' correctly not found in the conda definition",
                        self.main_nf,
                    )
                )
            else:
                self.failed.append(
                    (
                        "deprecated_enable_conda",
                        "Found deprecated parameter 'params.enable_conda' in the conda definition",
                        self.main_nf,
                    )
                )
        if _container_type(line) == "singularity":
            # e.g. "https://containers.biocontainers.pro/s3/SingImgsRepo/biocontainers/v1.2.0_cv1/biocontainers_v1.2.0_cv1.img -> v1.2.0_cv1
            # e.g. "https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0 -> 0.11.9--0
            # Please god let's find a better way to do this than regex
            match = re.search(r"(?:[:.])?([A-Za-z\d\-_.]+?)(?:\.img)?(?:\.sif)?$", line)
            if match is not None:
                singularity_tag = match.group(1)
                self.passed.append(("singularity_tag", f"Found singularity tag: {singularity_tag}", self.main_nf))
            else:
                self.failed.append(("singularity_tag", "Unable to parse singularity tag", self.main_nf))
                singularity_tag = None
            url = urlparse(line.split("'")[0])

        if _container_type(line) == "docker":
            # e.g. "quay.io/biocontainers/krona:2.7.1--pl526_5 -> 2.7.1--pl526_5
            # e.g. "biocontainers/biocontainers:v1.2.0_cv1 -> v1.2.0_cv1
            match = re.search(r":([A-Za-z\d\-_.]+)$", line)
            if match is not None:
                docker_tag = match.group(1)
                self.passed.append(("docker_tag", f"Found docker tag: {docker_tag}", self.main_nf))
            else:
                self.failed.append(("docker_tag", "Unable to parse docker tag", self.main_nf))
                docker_tag = None
            if line.startswith(registry):
                l_stripped = re.sub(r"\W+$", "", line)
                self.failed.append(
                    (
                        "container_links",
                        f"{l_stripped} container name found, please use just 'organisation/container:tag' instead.",
                        self.main_nf,
                    )
                )
            else:
                self.passed.append(("container_links", "Container prefix is correct", self.main_nf))

            # Guess if container name is simple one (e.g. nfcore/ubuntu:20.04)
            # If so, add quay.io as default container prefix
            if line.count("/") == 1 and line.count(":") == 1:
                line = "/".join([registry, line]).replace("//", "/")
            url = urlparse(line.split("'")[0])

        if line.startswith("container") or _container_type(line) == "docker" or _container_type(line) == "singularity":
            check_container_link_line(self, raw_line, registry)

        # Try to connect to container URLs
        if url is None:
            continue
        try:
            container_url = "https://" + urlunparse(url) if not url.scheme == "https" else urlunparse(url)
            response = requests.head(
                container_url,
                stream=True,
                allow_redirects=True,
            )
            log.debug(
                f"Connected to URL: {'https://' + urlunparse(url) if not url.scheme == 'https' else urlunparse(url)}, "
                f"status_code: {response.status_code}"
            )
        except (requests.exceptions.RequestException, sqlite3.InterfaceError) as e:
            log.debug(f"Unable to connect to url '{urlunparse(url)}' due to error: {e}")
            self.failed.append(("container_links", "Unable to connect to container URL", self.main_nf))
            continue
        if not response.ok:
            self.warned.append(
                (
                    "container_links",
                    f"Unable to connect to container registry, code:  {response.status_code}, url: {response.url}",
                    self.main_nf,
                )
            )

    # Get bioconda packages from environment.yml
    try:
        with open(Path(self.component_dir, "environment.yml")) as fh:
            env_yml = yaml.safe_load(fh)
        if "dependencies" in env_yml:
            bioconda_packages = [x for x in env_yml["dependencies"] if isinstance(x, str) and "bioconda::" in x]
    except FileNotFoundError:
        pass
    except NotADirectoryError:
        pass

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

    # Check if a tag exists at all. If not, return None.
    if singularity_tag is None or docker_tag is None:
        return None
    else:
        return docker_tag == singularity_tag


def check_process_labels(self, lines):
    correct_process_labels = ["process_single", "process_low", "process_medium", "process_high", "process_long"]
    all_labels = [line.strip() for line in lines if line.lstrip().startswith("label ")]
    bad_labels = []
    good_labels = []
    if len(all_labels) > 0:
        for label in all_labels:
            try:
                label = re.match(r"^label\s+'?([a-zA-Z0-9_-]+)'?$", label).group(1)
            except AttributeError:
                self.warned.append(
                    (
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
                    "process_standard_label",
                    f"Conflicting process labels found: `{'`,`'.join(good_labels)}`",
                    self.main_nf,
                )
            )
        elif len(good_labels) == 1:
            self.passed.append(("process_standard_label", "Correct process label", self.main_nf))
        else:
            self.warned.append(("process_standard_label", "Standard process label not found", self.main_nf))
        if len(bad_labels) > 0:
            self.warned.append(
                ("process_standard_label", f"Non-standard labels found: `{'`,`'.join(bad_labels)}`", self.main_nf)
            )
        if len(all_labels) > len(set(all_labels)):
            self.warned.append(
                (
                    "process_standard_label",
                    f"Duplicate labels found: `{'`,`'.join(sorted(all_labels))}`",
                    self.main_nf,
                )
            )
    else:
        self.warned.append(("process_standard_label", "Process label not specified", self.main_nf))


def check_container_link_line(self, raw_line, registry):
    """Look for common problems in the container name / URL, for docker and singularity."""

    line = raw_line.strip(" \n'\"}:")

    # lint double quotes
    if line.count('"') > 2:
        self.failed.append(
            (
                "container_links",
                f"Too many double quotes found when specifying container: {line.lstrip('container ')}",
                self.main_nf,
            )
        )
    else:
        self.passed.append(
            (
                "container_links",
                f"Correct number of double quotes found when specifying container: {line.lstrip('container ')}",
                self.main_nf,
            )
        )

    # Check for spaces in url
    single_quoted_items = raw_line.split("'")
    double_quoted_items = raw_line.split('"')
    # Look for container link as single item surrounded by quotes
    # (if there are multiple links, this will be warned in the next check)
    container_link = None
    if len(single_quoted_items) == 3:
        container_link = single_quoted_items[1]
    elif len(double_quoted_items) == 3:
        container_link = double_quoted_items[1]
    if container_link:
        if " " in container_link:
            self.failed.append(
                (
                    "container_links",
                    f"Space character found in container: '{container_link}'",
                    self.main_nf,
                )
            )
        else:
            self.passed.append(
                (
                    "container_links",
                    f"No space characters found in container: '{container_link}'",
                    self.main_nf,
                )
            )

        # lint more than one container in the same line
        if ("https://containers" in line or "https://depot" in line) and (
            "biocontainers/" in line or line.startswith(registry)
        ):
            self.warned.append(
                (
                    "container_links",
                    "Docker and Singularity containers specified in the same line. Only first one checked.",
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
    if "emit:" not in line:
        self.failed.append(("missing_emit", f"Missing emit statement: {line.strip()}", self.main_nf))
    else:
        output.append(line.split("emit:")[1].strip())

    return output


def _is_empty(line):
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

    with open(self.main_nf) as source:
        lines = source.readlines()

    # Check if the new version + build exist and replace
    new_lines = []
    for line in lines:
        line_stripped = line.strip(" '\"")
        build_type = _container_type(line_stripped)
        if build_type == "conda":
            new_lines.append(re.sub(rf"{current_version}", f"{latest_version}", line))
        elif build_type in ("singularity", "docker"):
            # Check that the new url is valid
            new_url = re.search(
                "(?:['\"])(.+)(?:['\"])", re.sub(rf"{singularity_tag}", f"{latest_version}--{build}", line)
            ).group(1)
            try:
                response_new_container = requests.get(
                    "https://" + new_url if not new_url.startswith("https://") else new_url, stream=True
                )
                log.debug(
                    f"Connected to URL: {'https://' + new_url if not new_url.startswith('https://') else new_url}, "
                    f"status_code: {response_new_container.status_code}"
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
    if line.startswith("conda"):
        return "conda"
    if line.startswith("https://") or line.startswith("https://depot"):
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
