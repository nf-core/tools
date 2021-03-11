#!/usr/bin/env python
"""Bumps the version number in all appropriate files for
a nf-core pipeline.
"""

import click
import logging
import os
import re
import rich.console
import sys
import nf_core.utils

log = logging.getLogger(__name__)
stderr = rich.console.Console(file=sys.stderr, force_terminal=nf_core.utils.rich_force_colors())


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
        log.error("Could not find config variable 'manifest.version'")
        sys.exit(1)
    log.info("Changing version number from '{}' to '{}'".format(current_version, new_version))

    # nextflow.config - workflow manifest version
    # nextflow.config - process container manifest version
    docker_tag = "dev"
    if new_version.replace(".", "").isdigit():
        docker_tag = new_version
    else:
        log.info("New version contains letters. Setting docker tag to 'dev'")

    update_file_version(
        "nextflow.config",
        pipeline_obj,
        [
            (
                r"version\s*=\s*[\'\"]?{}[\'\"]?".format(current_version.replace(".", r"\.")),
                "version = '{}'".format(new_version),
            ),
            (
                r"container\s*=\s*[\'\"]nfcore/{}:(?:{}|dev)[\'\"]".format(
                    pipeline_obj.pipeline_name.lower(), current_version.replace(".", r"\.")
                ),
                "container = 'nfcore/{}:{}'".format(pipeline_obj.pipeline_name.lower(), docker_tag),
            ),
        ],
    )

    # .github/workflows/ci.yml - docker build image tag
    # .github/workflows/ci.yml - docker tag image
    update_file_version(
        os.path.join(".github", "workflows", "ci.yml"),
        pipeline_obj,
        [
            (
                r"docker build --no-cache . -t nfcore/{name}:(?:{tag}|dev)".format(
                    name=pipeline_obj.pipeline_name.lower(), tag=current_version.replace(".", r"\.")
                ),
                "docker build --no-cache . -t nfcore/{name}:{tag}".format(
                    name=pipeline_obj.pipeline_name.lower(), tag=docker_tag
                ),
            ),
            (
                r"docker tag nfcore/{name}:dev nfcore/{name}:(?:{tag}|dev)".format(
                    name=pipeline_obj.pipeline_name.lower(), tag=current_version.replace(".", r"\.")
                ),
                "docker tag nfcore/{name}:dev nfcore/{name}:{tag}".format(
                    name=pipeline_obj.pipeline_name.lower(), tag=docker_tag
                ),
            ),
        ],
    )

    # environment.yml - environment name
    update_file_version(
        "environment.yml",
        pipeline_obj,
        [
            (
                r"name: nf-core-{}-{}".format(pipeline_obj.pipeline_name.lower(), current_version.replace(".", r"\.")),
                "name: nf-core-{}-{}".format(pipeline_obj.pipeline_name.lower(), new_version),
            )
        ],
    )

    # Dockerfile - ENV PATH and RUN conda env create
    update_file_version(
        "Dockerfile",
        pipeline_obj,
        [
            (
                r"nf-core-{}-{}".format(pipeline_obj.pipeline_name.lower(), current_version.replace(".", r"\.")),
                "nf-core-{}-{}".format(pipeline_obj.pipeline_name.lower(), new_version),
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
        log.error("Could not find config variable 'manifest.nextflowVersion'")
        sys.exit(1)
    log.info("Changing Nextlow version number from '{}' to '{}'".format(current_version, new_version))

    # nextflow.config - manifest minimum nextflowVersion
    update_file_version(
        "nextflow.config",
        pipeline_obj,
        [
            (
                r"nextflowVersion\s*=\s*[\'\"]?>={}[\'\"]?".format(current_version.replace(".", r"\.")),
                "nextflowVersion = '>={}'".format(new_version),
            )
        ],
    )

    # .github/workflows/ci.yml - Nextflow version matrix
    update_file_version(
        os.path.join(".github", "workflows", "ci.yml"),
        pipeline_obj,
        [
            (
                r"nxf_ver: \[[\'\"]?{}[\'\"]?, ''\]".format(current_version.replace(".", r"\.")),
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
                r"nextflow-%E2%89%A5{}-brightgreen.svg".format(current_version.replace(".", r"\.")),
                "nextflow-%E2%89%A5{}-brightgreen.svg".format(new_version),
            )
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

        # Check that we have a match
        matches_pattern = re.findall("^.*{}.*$".format(pattern[0]), content, re.MULTILINE)
        if len(matches_pattern) == 0:
            log.error("Could not find version number in {}: '{}'".format(filename, pattern))
            continue

        # Replace the match
        content = re.sub(pattern[0], pattern[1], content)
        matches_newstr = re.findall("^.*{}.*$".format(pattern[1]), content, re.MULTILINE)

        # Save for logging
        replacements.append((matches_pattern, matches_newstr))

    log.info("Updated version in '{}'".format(filename))
    for replacement in replacements:
        for idx, matched in enumerate(replacement[0]):
            stderr.print("          [red] - {}".format(matched.strip()), highlight=False)
            stderr.print("          [green] + {}".format(replacement[1][idx].strip()), highlight=False)
    stderr.print("\n")

    with open(fn, "w") as fh:
        fh.write(content)
