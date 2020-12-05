#!/usr/bin/env python

import os
import re


def readme(self):
    """Checks the repository README file for errors.

    Currently just checks the badges at the top of the README.
    """
    passed = []
    warned = []
    failed = []

    with open(os.path.join(self.path, "README.md"), "r") as fh:
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
    if "environment.yml" in self.files:
        bioconda_badge = "[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/)"
        if bioconda_badge in content:
            passed.append("README had a bioconda badge")
        else:
            warned.append("Found a bioconda environment.yml file but no badge in the README")

    return {"passed": passed, "warned": warned, "failed": failed}
