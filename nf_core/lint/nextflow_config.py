#!/usr/bin/env python

import re


def nextflow_config(self):
    """Checks a given pipeline for required config variables.

    At least one string in each list must be present for fail and warn.
    Any config in config_fail_ifdefined results in a failure.

    Uses ``nextflow config -flat`` to parse pipeline ``nextflow.config``
    and print all config variables.
    NB: Does NOT parse contents of main.nf / nextflow script
    """
    passed = []
    warned = []
    failed = []

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
    ]
    # Throw a warning if these are missing
    config_warn = [
        ["manifest.mainScript"],
        ["timeline.file"],
        ["trace.file"],
        ["report.file"],
        ["dag.file"],
        ["process.container"],
    ]
    # Old depreciated vars - fail if present
    config_fail_ifdefined = [
        "params.version",
        "params.nf_required_version",
        "params.container",
        "params.singleEnd",
        "params.igenomesIgnore",
    ]

    for cfs in config_fail:
        for cf in cfs:
            if cf in self.nf_config.keys():
                passed.append("Config variable found: {}".format(self._wrap_quotes(cf)))
                break
        else:
            failed.append("Config variable not found: {}".format(self._wrap_quotes(cfs)))
    for cfs in config_warn:
        for cf in cfs:
            if cf in self.nf_config.keys():
                passed.append("Config variable found: {}".format(self._wrap_quotes(cf)))
                break
        else:
            warned.append("Config variable not found: {}".format(self._wrap_quotes(cfs)))
    for cf in config_fail_ifdefined:
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
            passed.append("Config `{}` had correct value: `{}`".format(k, self.nf_config.get(k)))
        else:
            failed.append("Config `{}` did not have correct value: `{}`".format(k, self.nf_config.get(k)))

    # Check that the pipeline name starts with nf-core
    try:
        assert self.nf_config.get("manifest.name", "").strip("'\"").startswith("nf-core/")
    except (AssertionError, IndexError):
        failed.append(
            "Config `manifest.name` did not begin with `nf-core/`:\n    {}".format(
                self.nf_config.get("manifest.name", "").strip("'\"")
            )
        )
    else:
        passed.append("Config `manifest.name` began with `nf-core/`")

    # Check that the homePage is set to the GitHub URL
    try:
        assert self.nf_config.get("manifest.homePage", "").strip("'\"").startswith("https://github.com/nf-core/")
    except (AssertionError, IndexError):
        failed.append(
            "Config variable `manifest.homePage` did not begin with https://github.com/nf-core/:\n    {}".format(
                self.nf_config.get("manifest.homePage", "").strip("'\"")
            )
        )
    else:
        passed.append("Config variable `manifest.homePage` began with https://github.com/nf-core/")

    # Check that the DAG filename ends in `.svg`
    if "dag.file" in self.nf_config:
        if self.nf_config["dag.file"].strip("'\"").endswith(".svg"):
            passed.append("Config `dag.file` ended with `.svg`")
        else:
            failed.append("Config `dag.file` did not end with `.svg`")

    # Check that the minimum nextflowVersion is set properly
    if "manifest.nextflowVersion" in self.nf_config:
        if self.nf_config.get("manifest.nextflowVersion", "").strip("\"'").lstrip("!").startswith(">="):
            passed.append("Config variable `manifest.nextflowVersion` started with >= or !>=")
        else:
            failed.append(
                "Config `manifest.nextflowVersion` did not start with `>=` or `!>=` : `{}`".format(
                    self.nf_config.get("manifest.nextflowVersion", "")
                ).strip("\"'")
            )

    # Check that the process.container name is pulling the version tag or :dev
    if self.nf_config.get("process.container"):
        container_name = "{}:{}".format(
            self.nf_config.get("manifest.name").replace("nf-core", "nfcore").strip("'"),
            self.nf_config.get("manifest.version", "").strip("'"),
        )
        if "dev" in self.nf_config.get("manifest.version", "") or not self.nf_config.get("manifest.version"):
            container_name = "{}:dev".format(
                self.nf_config.get("manifest.name").replace("nf-core", "nfcore").strip("'")
            )
        try:
            assert self.nf_config.get("process.container", "").strip("'") == container_name
        except AssertionError:
            if self.release_mode:
                failed.append(
                    "Config `process.container` looks wrong. Should be `{}` but is `{}`".format(
                        container_name, self.nf_config.get("process.container", "").strip("'")
                    )
                )
            else:
                warned.append(
                    "Config `process.container` looks wrong. Should be `{}` but is `{}`".format(
                        container_name, self.nf_config.get("process.container", "").strip("'")
                    )
                )
        else:
            passed.append("Config `process.container` looks correct: `{}`".format(container_name))

    # Check that the pipeline version contains `dev`
    if not self.release_mode and "manifest.version" in self.nf_config:
        if self.nf_config["manifest.version"].strip(" '\"").endswith("dev"):
            passed.append("Config `manifest.version` ends in `dev`: `{}`".format(self.nf_config["manifest.version"]))
        else:
            warned.append(
                "Config `manifest.version` should end in `dev`: `{}`".format(self.nf_config["manifest.version"])
            )
    elif "manifest.version" in self.nf_config:
        if "dev" in self.nf_config["manifest.version"]:
            failed.append(
                "Config `manifest.version` should not contain `dev` for a release: `{}`".format(
                    self.nf_config["manifest.version"]
                )
            )
        else:
            passed.append(
                "Config `manifest.version` does not contain `dev` for release: `{}`".format(
                    self.nf_config["manifest.version"]
                )
            )
    return {"passed": passed, "warned": warned, "failed": failed}
