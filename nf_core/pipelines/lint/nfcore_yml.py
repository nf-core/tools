import re
from pathlib import Path
from typing import Dict, List

from nf_core import __version__

REPOSITORY_TYPES = ["pipeline", "modules"]


def nfcore_yml(self) -> Dict[str, List[str]]:
    """Repository ``.nf-core.yml`` tests

    The ``.nf-core.yml`` contains metadata for nf-core tools to correctly apply its features.

    * repository type:

        * Check that the repository type is set.

    * nf core version:

         * Check if the nf-core version is set to the latest version.

    """
    passed: List[str] = []
    warned: List[str] = []
    failed: List[str] = []
    ignored: List[str] = []

    # Remove field that should be ignored according to the linting config
    ignore_configs = self.lint_config.get(".nf-core", [])

    try:
        with open(Path(self.wf_path, ".nf-core.yml")) as fh:
            content = fh.read()
    except FileNotFoundError:
        with open(Path(self.wf_path, ".nf-core.yaml")) as fh:
            content = fh.read()

    if "repository_type" not in ignore_configs:
        # Check that the repository type is set in the .nf-core.yml
        repo_type_re = r"repository_type: (.+)"
        match = re.search(repo_type_re, content)
        if match:
            repo_type = match.group(1)
            if repo_type not in REPOSITORY_TYPES:
                failed.append(
                    f"Repository type in `.nf-core.yml` is not valid. "
                    f"Should be one of `[{', '.join(REPOSITORY_TYPES)}]` but was `{repo_type}`"
                )
            else:
                passed.append(f"Repository type in `.nf-core.yml` is valid: `{repo_type}`")
        else:
            warned.append("Repository type not set in `.nf-core.yml`")
    else:
        ignored.append("`.nf-core.yml` variable ignored 'repository_type'")

    if "nf_core_version" not in ignore_configs:
        # Check that the nf-core version is set in the .nf-core.yml
        nf_core_version_re = r"nf_core_version: (.+)"
        match = re.search(nf_core_version_re, content)
        if match:
            nf_core_version = match.group(1).strip('"')
            if nf_core_version != __version__ and "dev" not in nf_core_version:
                warned.append(
                    f"nf-core version in `.nf-core.yml` is not set to the latest version. "
                    f"Should be `{__version__}` but was `{nf_core_version}`"
                )
            else:
                passed.append(f"nf-core version in `.nf-core.yml` is set to the latest version: `{nf_core_version}`")
        else:
            warned.append("nf-core version not set in `.nf-core.yml`")
    else:
        ignored.append("`.nf-core.yml` variable ignored 'nf_core_version'")

    return {"passed": passed, "warned": warned, "failed": failed, "ignored": ignored}
