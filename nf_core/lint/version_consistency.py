#!/usr/bin/env python

import os


def version_consistency(self):
    """Pipeline and container version number consistency.

    .. note:: This test only runs when the ``--release`` flag is set for ``nf-core lint``,
              or ``$GITHUB_REF`` is equal to ``master``.

    This lint fetches the pipeline version number from three possible locations:

    * The pipeline config, ``manifest.version``
    * The docker container in the pipeline config, ``process.container``

        * Some pipelines may not have this set on a pipeline level. If it is not found, it is ignored.

    * ``$GITHUB_REF``, if it looks like a release tag (``refs/tags/<something>``)

    The test then checks that:

    * The container name has a tag specified (eg. ``nfcore/pipeline:version``)
    * The pipeline version number is numeric (contains only numbers and dots)
    * That the version numbers all match one another
    """
    passed = []
    failed = []

    # Get the version definitions
    # Get version from nextflow.config
    versions = {}
    versions["manifest.version"] = self.nf_config.get("manifest.version", "").strip(" '\"")

    # Get version from the docker tag
    if self.nf_config.get("process.container", "") and not ":" in self.nf_config.get("process.container", ""):
        failed.append(
            "Docker slug seems not to have a version tag: {}".format(self.nf_config.get("process.container", ""))
        )

    # Get config container tag (if set; one container per workflow)
    if self.nf_config.get("process.container", ""):
        versions["process.container"] = self.nf_config.get("process.container", "").strip(" '\"").split(":")[-1]

    # Get version from the $GITHUB_REF env var if this is a release
    if (
        os.environ.get("GITHUB_REF", "").startswith("refs/tags/")
        and os.environ.get("GITHUB_REPOSITORY", "") != "nf-core/tools"
    ):
        versions["GITHUB_REF"] = os.path.basename(os.environ["GITHUB_REF"].strip(" '\""))

    # Check if they are all numeric
    for v_type, version in versions.items():
        if not version.replace(".", "").isdigit():
            failed.append("{} was not numeric: {}!".format(v_type, version))

    # Check if they are consistent
    if len(set(versions.values())) != 1:
        failed.append(
            "The versioning is not consistent between container, release tag "
            "and config. Found {}".format(", ".join(["{} = {}".format(k, v) for k, v in versions.items()]))
        )

    passed.append("Version tags are numeric and consistent between container, release tag and config.")

    return {"passed": passed, "failed": failed}
