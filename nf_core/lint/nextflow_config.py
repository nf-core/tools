#!/usr/bin/env python

import re
import os
import logging

log = logging.getLogger(__name__)


def nextflow_config(self):
    """Checks the pipeline configuration for required variables.

    All nf-core pipelines are required to be configured with a minimal set of variable
    names. This test fails or throws warnings if required variables are not set.

    .. note:: These config variables must be set in ``nextflow.config`` or another config
              file imported from there. Any variables set in nextflow script files (eg. ``main.nf``)
              are not checked and will be assumed to be missing.

    **The following variables fail the test if missing:**

    * ``params.outdir``: A directory in which all pipeline results should be saved
    * ``manifest.name``: The pipeline name. Should begin with ``nf-core/``
    * ``manifest.description``: A description of the pipeline
    * ``manifest.version``

      * The version of this pipeline. This should correspond to a `GitHub release <https://help.github.com/articles/creating-releases/>`_.
      * If ``--release`` is set when running ``nf-core lint``, the version number must not contain the string ``dev``
      * If ``--release`` is _not_ set, the version should end in ``dev`` (warning triggered if not)

    * ``manifest.nextflowVersion``

      * The minimum version of Nextflow required to run the pipeline.
      * Should be ``>=`` or ``!>=`` and a version number, eg. ``manifest.nextflowVersion = '>=0.31.0'`` (see `Nextflow documentation <https://www.nextflow.io/docs/latest/config.html#scope-manifest>`_)
      * ``>=`` warns about old versions but tries to run anyway, ``!>=`` fails for old versions. Only use the latter if you *know* that the pipeline will certainly fail before this version.
      * This should correspond to the ``NXF_VER`` version tested by GitHub Actions.

    * ``manifest.homePage``

      * The homepage for the pipeline. Should be the nf-core GitHub repository URL,
        so beginning with ``https://github.com/nf-core/``

    * ``timeline.enabled``, ``trace.enabled``, ``report.enabled``, ``dag.enabled``

      * The nextflow timeline, trace, report and DAG should be enabled by default (set to ``true``)

    * ``process.cpus``, ``process.memory``, ``process.time``

      * Default CPUs, memory and time limits for tasks

    * ``params.input``

      * Input parameter to specify input data, specify this to avoid a warning
      * Typical usage:

        * ``params.input``: Input data that is not NGS sequencing data

    * ``params.custom_config_version``

        * Should always be set to default value ``master``

    * ``params.custom_config_base``

        * Should always be set to default value:
        ``https://raw.githubusercontent.com/nf-core/configs/${params.custom_config_version}``

    * ``params.show_hidden_params``

        * Determines whether boilerplate params are showed by schema. Set to ``false`` by default

    * ``params.schema_ignore_params``

        * A comma separated string of inputs the schema validation should ignore.

    **The following variables throw warnings if missing:**

    * ``manifest.mainScript``: The filename of the main pipeline script (should be ``main.nf``)
    * ``timeline.file``, ``trace.file``, ``report.file``, ``dag.file``

      * Default filenames for the timeline, trace and report
      * The DAG file path should end with ``.svg`` (If Graphviz is not installed, Nextflow will generate a ``.dot`` file instead)

    **The following variables are depreciated and fail the test if they are still present:**

    * ``params.version``: The old method for specifying the pipeline version. Replaced by ``manifest.version``
    * ``params.nf_required_version``: The old method for specifying the minimum Nextflow version. Replaced by ``manifest.nextflowVersion``
    * ``params.container``: The old method for specifying the dockerhub container address. Replaced by ``process.container``
    * ``igenomesIgnore``: Changed to ``igenomes_ignore``

        .. tip:: The ``snake_case`` convention should now be used when defining pipeline parameters

    **The following Nextflow syntax is depreciated and fails the test if present:**

    * Process-level configuration syntax still using the old Nextflow syntax, for example: ``process.$fastqc`` instead of ``process withName:'fastqc'``.

    .. tip:: You can choose to ignore tests for the presence or absence of specific config variables
             by creating a file called ``.nf-core-lint.yml`` in the root of your pipeline and creating
             a list the config variables that should be ignored. For example:

             .. code-block:: yaml

                nextflow_config:
                    - params.input

             The other checks in this test (depreciated syntax etc) can not be individually identified,
             but you can skip the entire test block if you wish:

             .. code-block:: yaml

                nextflow_config: False
    """
    passed = []
    warned = []
    failed = []
    ignored = []

    # Fail tests if these are missing
    config_fail = [
        ["manifest.name"],
        ["manifest.nextflowVersion"],
        ["manifest.description"],
        ["manifest.version"],
        ["manifest.homePage"],
        ["timeline.enabled"],
        ["trace.enabled"],
        ["report.enabled"],
        ["dag.enabled"],
        ["process.cpus"],
        ["process.memory"],
        ["process.time"],
        ["params.outdir"],
        ["params.input"],
        ["params.show_hidden_params"],
        ["params.schema_ignore_params"],
    ]
    # Throw a warning if these are missing
    config_warn = [
        ["manifest.mainScript"],
        ["timeline.file"],
        ["trace.file"],
        ["report.file"],
        ["dag.file"],
    ]
    # Old depreciated vars - fail if present
    config_fail_ifdefined = [
        "params.version",
        "params.nf_required_version",
        "params.container",
        "params.singleEnd",
        "params.igenomesIgnore",
        "params.name",
    ]

    # Remove field that should be ignored according to the linting config
    ignore_configs = self.lint_config.get("nextflow_config", [])

    for cfs in config_fail:
        for cf in cfs:
            if cf in ignore_configs:
                ignored.append("Config variable ignored: {}".format(self._wrap_quotes(cf)))
                break
            if cf in self.nf_config.keys():
                passed.append("Config variable found: {}".format(self._wrap_quotes(cf)))
                break
        else:
            failed.append("Config variable not found: {}".format(self._wrap_quotes(cfs)))
    for cfs in config_warn:
        for cf in cfs:
            if cf in ignore_configs:
                ignored.append("Config variable ignored: {}".format(self._wrap_quotes(cf)))
                break
            if cf in self.nf_config.keys():
                passed.append("Config variable found: {}".format(self._wrap_quotes(cf)))
                break
        else:
            warned.append("Config variable not found: {}".format(self._wrap_quotes(cfs)))
    for cf in config_fail_ifdefined:
        if cf in ignore_configs:
            ignored.append("Config variable ignored: {}".format(self._wrap_quotes(cf)))
            break
        if cf not in self.nf_config.keys():
            passed.append("Config variable (correctly) not found: {}".format(self._wrap_quotes(cf)))
        else:
            failed.append("Config variable (incorrectly) found: {}".format(self._wrap_quotes(cf)))

    # Check and warn if the process configuration is done with deprecated syntax
    process_with_deprecated_syntax = list(
        set(
            [
                re.search(r"^(process\.\$.*?)\.+.*$", ck).group(1)
                for ck in self.nf_config.keys()
                if re.match(r"^(process\.\$.*?)\.+.*$", ck)
            ]
        )
    )
    for pd in process_with_deprecated_syntax:
        warned.append("Process configuration is done with deprecated_syntax: {}".format(pd))

    # Check the variables that should be set to 'true'
    for k in ["timeline.enabled", "report.enabled", "trace.enabled", "dag.enabled"]:
        if self.nf_config.get(k) == "true":
            passed.append("Config ``{}`` had correct value: ``{}``".format(k, self.nf_config.get(k)))
        else:
            failed.append("Config ``{}`` did not have correct value: ``{}``".format(k, self.nf_config.get(k)))

    # Check that the pipeline name starts with nf-core
    try:
        assert self.nf_config.get("manifest.name", "").strip("'\"").startswith("nf-core/")
    except (AssertionError, IndexError):
        failed.append(
            "Config ``manifest.name`` did not begin with ``nf-core/``:\n    {}".format(
                self.nf_config.get("manifest.name", "").strip("'\"")
            )
        )
    else:
        passed.append("Config ``manifest.name`` began with ``nf-core/``")

    # Check that the homePage is set to the GitHub URL
    try:
        assert self.nf_config.get("manifest.homePage", "").strip("'\"").startswith("https://github.com/nf-core/")
    except (AssertionError, IndexError):
        failed.append(
            "Config variable ``manifest.homePage`` did not begin with https://github.com/nf-core/:\n    {}".format(
                self.nf_config.get("manifest.homePage", "").strip("'\"")
            )
        )
    else:
        passed.append("Config variable ``manifest.homePage`` began with https://github.com/nf-core/")

    # Check that the DAG filename ends in ``.svg``
    if "dag.file" in self.nf_config:
        if self.nf_config["dag.file"].strip("'\"").endswith(".svg"):
            passed.append("Config ``dag.file`` ended with ``.svg``")
        else:
            failed.append("Config ``dag.file`` did not end with ``.svg``")

    # Check that the minimum nextflowVersion is set properly
    if "manifest.nextflowVersion" in self.nf_config:
        if self.nf_config.get("manifest.nextflowVersion", "").strip("\"'").lstrip("!").startswith(">="):
            passed.append("Config variable ``manifest.nextflowVersion`` started with >= or !>=")
        else:
            failed.append(
                "Config ``manifest.nextflowVersion`` did not start with ``>=`` or ``!>=`` : ``{}``".format(
                    self.nf_config.get("manifest.nextflowVersion", "")
                ).strip("\"'")
            )

    # Check that the pipeline version contains ``dev``
    if not self.release_mode and "manifest.version" in self.nf_config:
        if self.nf_config["manifest.version"].strip(" '\"").endswith("dev"):
            passed.append(
                "Config ``manifest.version`` ends in ``dev``: ``{}``".format(self.nf_config["manifest.version"])
            )
        else:
            warned.append(
                "Config ``manifest.version`` should end in ``dev``: ``{}``".format(self.nf_config["manifest.version"])
            )
    elif "manifest.version" in self.nf_config:
        if "dev" in self.nf_config["manifest.version"]:
            failed.append(
                "Config ``manifest.version`` should not contain ``dev`` for a release: ``{}``".format(
                    self.nf_config["manifest.version"]
                )
            )
        else:
            passed.append(
                "Config ``manifest.version`` does not contain ``dev`` for release: ``{}``".format(
                    self.nf_config["manifest.version"]
                )
            )

    # Check if custom profile params are set correctly
    if self.nf_config.get("params.custom_config_version", "").strip("'") == "master":
        passed.append("Config `params.custom_config_version` is set to `master`")
    else:
        failed.append("Config `params.custom_config_version` is not set to `master`")

    custom_config_base = "https://raw.githubusercontent.com/nf-core/configs/{}".format(
        self.nf_config.get("params.custom_config_version", "").strip("'")
    )
    if self.nf_config.get("params.custom_config_base", "").strip("'") == custom_config_base:
        passed.append("Config `params.custom_config_base` is set to `{}`".format(custom_config_base))
    else:
        failed.append("Config `params.custom_config_base` is not set to `{}`".format(custom_config_base))

    # Check that lines for loading custom profiles exist
    lines = [
        r"// Load nf-core custom profiles from different Institutions",
        r"try {",
        r'includeConfig "${params.custom_config_base}/nfcore_custom.config"',
        r"} catch (Exception e) {",
        r'System.err.println("WARNING: Could not load nf-core/config profiles: ${params.custom_config_base}/nfcore_custom.config")',
        r"}",
    ]
    path = os.path.join(self.wf_path, "nextflow.config")
    i = 0
    with open(path, "r") as f:
        for line in f:
            if lines[i] in line:
                i += 1
                if i == len(lines):
                    break
            else:
                i = 0
    if i == len(lines):
        passed.append("Lines for loading custom profiles found")
    else:
        lines[2] = f"\t{lines[2]}"
        lines[4] = f"\t{lines[4]}"
        failed.append(
            "Lines for loading custom profiles not found. File should contain: ```groovy\n{}".format("\n".join(lines))
        )

    return {"passed": passed, "warned": warned, "failed": failed, "ignored": ignored}
