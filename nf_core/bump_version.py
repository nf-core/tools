#!/usr/bin/env python
"""Bumps the version number in all appropriate files for
a nf-core pipeline.
"""

import logging
import os
import re
import rich.console
import sys
import nf_core.utils

log = logging.getLogger(__name__)
stderr = rich.console.Console(stderr=True, force_terminal=nf_core.utils.rich_force_colors())


def bump_pipeline_version(pipeline_obj, new_version):
    """Bumps a pipeline version number.

    Args:
        pipeline_obj (nf_core.utils.Pipeline): A `Pipeline` object that holds information
            about the pipeline contents and build files.
        new_version (str): The new version tag for the pipeline. Semantic versioning only.
    """

    # Collect the old and new version numbers
    current_version = pipeline_obj.nf_config.get("manifest.version", "").strip(" '\"")
    if new_version.startswith("v"):
        log.warning("Stripping leading 'v' from new version number")
        new_version = new_version[1:]
    if not current_version:
        raise UserWarning("Could not find config variable 'manifest.version'")

    log.info("Changing version number from '{}' to '{}'".format(current_version, new_version))

    # nextflow.config - workflow manifest version
    update_file_version(
        "nextflow.config",
        pipeline_obj,
        [
            (
                r"version\s*=\s*[\'\"]?{}[\'\"]?".format(current_version.replace(".", r"\.")),
                "version = '{}'".format(new_version),
            )
        ],
    )


def bump_nextflow_version(pipeline_obj, new_version):
    """Bumps the required Nextflow version number of a pipeline.

    Args:
        pipeline_obj (nf_core.utils.Pipeline): A `Pipeline` object that holds information
            about the pipeline contents and build files.
        new_version (str): The new version tag for the required Nextflow version.
    """

    # Collect the old and new version numbers - strip leading non-numeric characters (>=)
    current_version = pipeline_obj.nf_config.get("manifest.nextflowVersion", "").strip(" '\"")
    current_version = re.sub(r"^[^0-9\.]*", "", current_version)
    new_version = re.sub(r"^[^0-9\.]*", "", new_version)
    if not current_version:
        raise UserWarning("Could not find config variable 'manifest.nextflowVersion'")
    log.info("Changing Nextlow version number from '{}' to '{}'".format(current_version, new_version))

    # nextflow.config - manifest minimum nextflowVersion
    update_file_version(
        "nextflow.config",
        pipeline_obj,
        [
            (
                r"nextflowVersion\s*=\s*[\'\"]?!>={}[\'\"]?".format(current_version.replace(".", r"\.")),
                "nextflowVersion = '!>={}'".format(new_version),
            )
        ],
    )

    # .github/workflows/ci.yml - Nextflow version matrix
    update_file_version(
        os.path.join(".github", "workflows", "ci.yml"),
        pipeline_obj,
        [
            (
                # example: nxf_ver: ['20.04.0', '']
                r"nxf_ver: \[[\'\"]{}[\'\"], [\'\"][\'\"]\]".format(current_version.replace(".", r"\.")),
                "nxf_ver: ['{}', '']".format(new_version),
            )
        ],
    )

    # README.md - Nextflow version badge
    update_file_version(
        "README.md",
        pipeline_obj,
        [
            (
                r"nextflow%20DSL2-%E2%89%A5{}-23aa62.svg".format(current_version.replace(".", r"\.")),
                "nextflow%20DSL2-%E2%89%A5{}-23aa62.svg".format(new_version),
            ),
            (
                # example: 1. Install [`Nextflow`](https://www.nextflow.io/docs/latest/getstarted.html#installation) (`>=20.04.0`)
                r"1\.\s*Install\s*\[`Nextflow`\]\(https://www.nextflow.io/docs/latest/getstarted.html#installation\)\s*\(`>={}`\)".format(
                    current_version.replace(".", r"\.")
                ),
                "1. Install [`Nextflow`](https://www.nextflow.io/docs/latest/getstarted.html#installation) (`>={}`)".format(
                    new_version
                ),
            ),
        ],
    )


def update_file_version(filename, pipeline_obj, patterns):
    """Updates the version number in a requested file.

    Args:
        filename (str): File to scan.
        pipeline_obj (nf_core.lint.PipelineLint): A PipelineLint object that holds information
            about the pipeline contents and build files.
        pattern (str): Regex pattern to apply.
        newstr (str): The replaced string.

    Raises:
        ValueError, if the version number cannot be found.
    """
    # Load the file
    fn = pipeline_obj._fp(filename)
    content = ""
    try:
        with open(fn, "r") as fh:
            content = fh.read()
    except FileNotFoundError:
        log.warning("File not found: '{}'".format(fn))
        return

    replacements = []
    for pattern in patterns:

        found_match = False

        newcontent = []
        for line in content.splitlines():

            # Match the pattern
            matches_pattern = re.findall("^.*{}.*$".format(pattern[0]), line)
            if matches_pattern:
                found_match = True

                # Replace the match
                newline = re.sub(pattern[0], pattern[1], line)
                newcontent.append(newline)

                # Save for logging
                replacements.append((line, newline))

            # No match, keep line as it is
            else:
                newcontent.append(line)

        if found_match:
            content = "\n".join(newcontent)
        else:
            log.error("Could not find version number in {}: '{}'".format(filename, pattern))

    log.info("Updated version in '{}'".format(filename))
    for replacement in replacements:
        stderr.print("          [red] - {}".format(replacement[0].strip()), highlight=False)
        stderr.print("          [green] + {}".format(replacement[1].strip()), highlight=False)
    stderr.print("\n")

    with open(fn, "w") as fh:
        fh.write(content)
