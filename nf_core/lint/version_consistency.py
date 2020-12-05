#!/usr/bin/env python


def version_consistency(self):
    """Checks container tags versions.

    Runs on ``process.container`` (if set) and ``$GITHUB_REF`` (if a GitHub Actions release).

    Checks that:
        * the container has a tag
        * the version numbers are numeric
        * the version numbers are the same as one-another
    """
    passed = []
    warned = []
    failed = []

    versions = {}
    # Get the version definitions
    # Get version from nextflow.config
    versions["manifest.version"] = self.config.get("manifest.version", "").strip(" '\"")

    # Get version from the docker slug
    if self.config.get("process.container", "") and not ":" in self.config.get("process.container", ""):
        failed.append(
            "Docker slug seems not to have a version tag: {}".format(self.config.get("process.container", ""))
        )
        return

    # Get config container slugs, (if set; one container per workflow)
    if self.config.get("process.container", ""):
        versions["process.container"] = self.config.get("process.container", "").strip(" '\"").split(":")[-1]
    if self.config.get("process.container", ""):
        versions["process.container"] = self.config.get("process.container", "").strip(" '\"").split(":")[-1]

    # Get version from the GITHUB_REF env var if this is a release
    if (
        os.environ.get("GITHUB_REF", "").startswith("refs/tags/")
        and os.environ.get("GITHUB_REPOSITORY", "") != "nf-core/tools"
    ):
        versions["GITHUB_REF"] = os.path.basename(os.environ["GITHUB_REF"].strip(" '\""))

    # Check if they are all numeric
    for v_type, version in versions.items():
        if not version.replace(".", "").isdigit():
            failed.append("{} was not numeric: {}!".format(v_type, version))
            return

    # Check if they are consistent
    if len(set(versions.values())) != 1:
        failed.append(
            "The versioning is not consistent between container, release tag "
            "and config. Found {}".format(", ".join(["{} = {}".format(k, v) for k, v in versions.items()]))
        )
        return

    passed.append("Version tags are numeric and consistent between container, release tag and config.")

    return {"passed": passed, "warned": warned, "failed": failed}
