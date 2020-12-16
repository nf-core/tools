#!/usr/bin/env python

import os
import re


def readme(self):
    """Repository ``README.md`` tests

    The ``README.md`` files for a project are very important and must meet some requirements:

    * Nextflow badge

      * If no Nextflow badge is found, a warning is given
      * If a badge is found but the version doesn't match the minimum version in the config file, the test fails
      * Example badge code:

        .. code-block:: md

           [![Nextflow](https://img.shields.io/badge/nextflow-%E2%89%A50.27.6-brightgreen.svg)](https://www.nextflow.io/)

    * Bioconda badge

      * If your pipeline contains a file called ``environment.yml`` in the root directory, a bioconda badge is required
      * Required badge code:

        .. code-block:: md

           [![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/)

    .. note:: These badges are a markdown image ``![alt-text](<image URL>)`` *inside* a markdown link ``[markdown image](<link URL>)``, so a bit fiddly to write.
    """
    passed = []
    warned = []
    failed = []

    with open(os.path.join(self.wf_path, "README.md"), "r") as fh:
        content = fh.read()

    # Check that there is a readme badge showing the minimum required version of Nextflow
    # and that it has the correct version
    nf_badge_re = r"\[!\[Nextflow\]\(https://img\.shields\.io/badge/nextflow-%E2%89%A5([\d\.]+)-brightgreen\.svg\)\]\(https://www\.nextflow\.io/\)"
    match = re.search(nf_badge_re, content)
    if match:
        nf_badge_version = match.group(1).strip("'\"")
        try:
            assert nf_badge_version == self.minNextflowVersion
        except (AssertionError, KeyError):
            failed.append(
                "README Nextflow minimum version badge does not match config. Badge: `{}`, Config: `{}`".format(
                    nf_badge_version, self.minNextflowVersion
                )
            )
        else:
            passed.append(
                "README Nextflow minimum version badge matched config. Badge: `{}`, Config: `{}`".format(
                    nf_badge_version, self.minNextflowVersion
                )
            )
    else:
        warned.append("README did not have a Nextflow minimum version badge.")

    # Check that we have a bioconda badge if we have a bioconda environment file
    if os.path.join(self.wf_path, "environment.yml") in self.files:
        bioconda_badge = "[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/)"
        if bioconda_badge in content:
            passed.append("README had a bioconda badge")
        else:
            warned.append("Found a bioconda environment.yml file but no badge in the README")

    return {"passed": passed, "warned": warned, "failed": failed}
