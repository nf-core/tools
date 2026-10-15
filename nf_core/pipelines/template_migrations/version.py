"""Read and stamp `nf_core_version` without rewriting the rest of .nf-core.yml."""

import re

from nf_core.utils import CONFIG_PATHS

# The pipeline's tools config: .nf-core.yml, or .nf-core.yaml.
NF_CORE_CONFIG_PATHS = tuple(CONFIG_PATHS)

# A line-level edit keeps the pipeline's comments and key order, which a
# YAML round trip would not.
VERSION_LINE = re.compile(r"^nf_core_version:[ \t]*(\S+)[ \t]*$", re.MULTILINE)


def parse_version(nf_core_yml: str) -> str | None:
    match = VERSION_LINE.search(nf_core_yml)
    if match is None:
        return None
    return match.group(1).strip("'\"")


def stamp_version(nf_core_yml: str, version: str) -> str:
    new_line = f"nf_core_version: {version}"
    if VERSION_LINE.search(nf_core_yml) is None:
        return f"{new_line}\n{nf_core_yml}"
    return VERSION_LINE.sub(new_line, nf_core_yml, count=1)
