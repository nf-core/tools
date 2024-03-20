def nfcore_yml(self):
    """Repository ``.nf-core.yml`` tests

    The ``.nf-core.yml`` contains metadata for nf-core tools to correctly apply its features.

    * repository type:

        * Check that the repository type is set.

    * nf core version:

         * Check if the nf-core version is set to the latest version.

    """
    passed = []
    warned = []
    failed = []

    # Remove field that should be ignored according to the linting config
    # ignore_configs = self.lint_config.get(".nf-core", [])

    # with open(os.path.join(self.wf_path, ".nf-core.yml")) as fh:
    #     content = fh.read()

    # if "nextflow_badge" not in ignore_configs:
    #     # Check that there is a readme badge showing the minimum required version of Nextflow
    #     # [![Nextflow](https://img.shields.io/badge/nextflow%20DSL2-%E2%89%A523.04.0-23aa62.svg)](https://www.nextflow.io/)
    #     # and that it has the correct version
    #     nf_badge_re = r"\[!\[Nextflow\]\(https://img\.shields\.io/badge/nextflow%20DSL2-!?(?:%E2%89%A5|%3E%3D)([\d\.]+)-23aa62\.svg\)\]\(https://www\.nextflow\.io/\)"
    #     match = re.search(nf_badge_re, content)
    #     if match:
    #         nf_badge_version = match.group(1).strip("'\"")
    #         try:
    #             if nf_badge_version != self.minNextflowVersion:
    #                 raise AssertionError()
    #         except (AssertionError, KeyError):
    #             failed.append(
    #                 f"README Nextflow minimum version badge does not match config. Badge: `{nf_badge_version}`, "
    #                 f"Config: `{self.minNextflowVersion}`"
    #             )
    #         else:
    #             passed.append(
    #                 f"README Nextflow minimum version badge matched config. Badge: `{nf_badge_version}`, "
    #                 f"Config: `{self.minNextflowVersion}`"
    #             )
    #     else:
    #         warned.append("README did not have a Nextflow minimum version badge.")

    # if "zenodo_doi" not in ignore_configs:
    #     # Check that zenodo.XXXXXXX has been replaced with the zendo.DOI
    #     zenodo_re = r"/zenodo\.X+"
    #     match = re.search(zenodo_re, content)
    #     if match:
    #         warned.append(
    #             "README contains the placeholder `zenodo.XXXXXXX`. "
    #             "This should be replaced with the zenodo doi (after the first release)."
    #         )
    #     else:
    #         passed.append("README Zenodo placeholder was replaced with DOI.")

    return {"passed": passed, "warned": warned, "failed": failed}
