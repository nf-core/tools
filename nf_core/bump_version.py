"""Bumps the version number in all appropriate files for
a nf-core pipeline.
"""

import logging
import re
from pathlib import Path

import rich.console

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

    log.info(f"Changing version number from '{current_version}' to '{new_version}'")

    # nextflow.config - workflow manifest version
    update_file_version(
        "nextflow.config",
        pipeline_obj,
        [
            (
                rf"version\s*=\s*[\'\"]?{re.escape(current_version)}[\'\"]?",
                f"version = '{new_version}'",
            )
        ],
    )
    # multiqc_config.yaml
    multiqc_new_version = "dev" if "dev" in new_version else new_version
    update_file_version(
        Path("assets", "multiqc_config.yml"),
        pipeline_obj,
        [
            (
                "/dev",
                f"/{multiqc_new_version}",
            ),
            (
                rf"{re.escape(current_version)}",
                f"{multiqc_new_version}",
            ),
        ],
    )
    # nf-test snap files
    pipeline_name = pipeline_obj.nf_config.get("manifest.name", "").strip(" '\"")
    snap_files = [f for f in Path().glob("tests/pipeline/*.snap")]
    for snap_file in snap_files:
        update_file_version(
            snap_file,
            pipeline_obj,
            [
                (
                    f"{pipeline_name}={current_version}",
                    f"{pipeline_name}={new_version}",
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
    log.info(f"Changing Nextlow version number from '{current_version}' to '{new_version}'")

    # nextflow.config - manifest minimum nextflowVersion
    update_file_version(
        "nextflow.config",
        pipeline_obj,
        [
            (
                rf"nextflowVersion\s*=\s*[\'\"]?!>={re.escape(current_version)}[\'\"]?",
                f"nextflowVersion = '!>={new_version}'",
            )
        ],
    )

    # .github/workflows/ci.yml - Nextflow version matrix
    update_file_version(
        Path(".github", "workflows", "ci.yml"),
        pipeline_obj,
        [
            (
                # example:
                # NXF_VER:
                #   - "20.04.0"
                rf"- [\"]{re.escape(current_version)}[\"]",
                f'- "{new_version}"',
            )
        ],
    )

    # README.md - Nextflow version badge
    update_file_version(
        "README.md",
        pipeline_obj,
        [
            (
                rf"nextflow%20DSL2-%E2%89%A5{re.escape(current_version)}-23aa62.svg",
                f"nextflow%20DSL2-%E2%89%A5{new_version}-23aa62.svg",
            ),
            (
                # example: 1. Install [`Nextflow`](https://www.nextflow.io/docs/latest/getstarted.html#installation) (`>=20.04.0`)
                rf"1\.\s*Install\s*\[`Nextflow`\]\(https:\/\/www\.nextflow\.io\/docs\/latest\/getstarted\.html#installation\)\s*\(`>={re.escape(current_version)}`\)",
                f"1. Install [`Nextflow`](https://www.nextflow.io/docs/latest/getstarted.html#installation) (`>={new_version}`)",
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
        log.warning(f"File not found: '{fn}'")
        return

    replacements = []
    for pattern in patterns:
        found_match = False

        newcontent = []
        for line in content.splitlines():
            # Match the pattern
            matches_pattern = re.findall(rf"^.*{pattern[0]}.*$", line)
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
            content = "\n".join(newcontent) + "\n"
        else:
            log.error(f"Could not find version number in {filename}: '{pattern}'")

    log.info(f"Updated version in '{filename}'")
    for replacement in replacements:
        stderr.print(f"          [red] - {replacement[0].strip()}", highlight=False)
        stderr.print(f"          [green] + {replacement[1].strip()}", highlight=False)
    stderr.print("\n")

    with open(fn, "w") as fh:
        fh.write(content)
