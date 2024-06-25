import logging
import os
import re
from pathlib import Path

from nf_core.schema import PipelineSchema

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

    * ``params.validationShowHiddenParams``

        * Determines whether boilerplate params are showed by schema. Set to ``false`` by default

    * ``params.validationSchemaIgnoreParams``

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
             by creating a file called ``.nf-core.yml`` in the root of your pipeline and creating
             a list the config variables that should be ignored. For example:

             .. code-block:: yaml

                lint:
                    nextflow_config:
                        - params.input

             The other checks in this test (depreciated syntax etc) can not be individually identified,
             but you can skip the entire test block if you wish:

             .. code-block:: yaml

                lint:
                    nextflow_config: False

    **The configuration should contain the following or the test will fail:**

    * A ``test`` configuration profile should exist.

    **The default values in ``nextflow.config`` should match the default values defined in the ``nextflow_schema.json``.**

    .. tip:: You can choose to ignore tests for the default value of an specific parameter
             by creating a file called ``.nf-core.yml`` in the root of your pipeline and creating
             a list the config parameters that should be ignored. For example to ignore the default value for the input parameter:

             .. code-block:: yaml

                lint:
                    nextflow_config:
                        - config_defaults:
                            - params.input
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
        ["params.validationShowHiddenParams"],
        ["params.validationSchemaIgnoreParams"],
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
        "params.nf_required_version",
        "params.container",
        "params.singleEnd",
        "params.igenomesIgnore",
        "params.name",
        "params.enable_conda",
    ]

    # Remove field that should be ignored according to the linting config
    ignore_configs = self.lint_config.get("nextflow_config", [])

    for cfs in config_fail:
        for cf in cfs:
            if cf in ignore_configs:
                ignored.append(f"Config variable ignored: {self._wrap_quotes(cf)}")
                break
            if cf in self.nf_config.keys():
                passed.append(f"Config variable found: {self._wrap_quotes(cf)}")
                break
        else:
            failed.append(f"Config variable not found: {self._wrap_quotes(cfs)}")
    for cfs in config_warn:
        for cf in cfs:
            if cf in ignore_configs:
                ignored.append(f"Config variable ignored: {self._wrap_quotes(cf)}")
                break
            if cf in self.nf_config.keys():
                passed.append(f"Config variable found: {self._wrap_quotes(cf)}")
                break
        else:
            warned.append(f"Config variable not found: {self._wrap_quotes(cfs)}")
    for cf in config_fail_ifdefined:
        if cf in ignore_configs:
            ignored.append(f"Config variable ignored: {self._wrap_quotes(cf)}")
            break
        if cf not in self.nf_config.keys():
            passed.append(f"Config variable (correctly) not found: {self._wrap_quotes(cf)}")
        else:
            failed.append(f"Config variable (incorrectly) found: {self._wrap_quotes(cf)}")

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
        warned.append(f"Process configuration is done with deprecated_syntax: {pd}")

    # Check the variables that should be set to 'true'
    for k in ["timeline.enabled", "report.enabled", "trace.enabled", "dag.enabled"]:
        if k in ignore_configs:
            continue
        if self.nf_config.get(k) == "true":
            passed.append(f"Config ``{k}`` had correct value: ``{self.nf_config.get(k)}``")
        else:
            failed.append(f"Config ``{k}`` did not have correct value: ``{self.nf_config.get(k)}``")

    if "manifest.name" not in ignore_configs:
        # Check that the pipeline name starts with nf-core
        try:
            manifest_name = self.nf_config.get("manifest.name", "").strip("'\"")
            if not manifest_name.startswith("nf-core/"):
                raise AssertionError()
        except (AssertionError, IndexError):
            failed.append(f"Config ``manifest.name`` did not begin with ``nf-core/``:\n    {manifest_name}")
        else:
            passed.append("Config ``manifest.name`` began with ``nf-core/``")

    if "manifest.homePage" not in ignore_configs:
        # Check that the homePage is set to the GitHub URL
        try:
            manifest_homepage = self.nf_config.get("manifest.homePage", "").strip("'\"")
            if not manifest_homepage.startswith("https://github.com/nf-core/"):
                raise AssertionError()
        except (AssertionError, IndexError):
            failed.append(
                f"Config variable ``manifest.homePage`` did not begin with https://github.com/nf-core/:\n    {manifest_homepage}"
            )

        else:
            passed.append("Config variable ``manifest.homePage`` began with https://github.com/nf-core/")

    # Check that the DAG filename ends in ``.svg``
    if "dag.file" in self.nf_config:
        default_dag_format = ".html"
        if self.nf_config["dag.file"].strip("'\"").endswith(default_dag_format):
            passed.append(f"Config ``dag.file`` ended with ``{default_dag_format}``")
        else:
            failed.append(f"Config ``dag.file`` did not end with ``{default_dag_format}``")

    # Check that the minimum nextflowVersion is set properly
    if "manifest.nextflowVersion" in self.nf_config:
        if self.nf_config.get("manifest.nextflowVersion", "").strip("\"'").lstrip("!").startswith(">="):
            passed.append("Config variable ``manifest.nextflowVersion`` started with >= or !>=")
        else:
            failed.append(
                "Config ``manifest.nextflowVersion`` did not start with ``>=`` or ``!>=`` : "
                f"``{self.nf_config.get('manifest.nextflowVersion', '')}``".strip("\"'")
            )

    # Check that the pipeline version contains ``dev``
    if not self.release_mode and "manifest.version" in self.nf_config:
        if self.nf_config["manifest.version"].strip(" '\"").endswith("dev"):
            passed.append(f"Config ``manifest.version`` ends in ``dev``: ``{self.nf_config['manifest.version']}``")
        else:
            warned.append(
                f"Config ``manifest.version`` should end in ``dev``: ``{self.nf_config['manifest.version']}``"
            )
    elif "manifest.version" in self.nf_config:
        if "dev" in self.nf_config["manifest.version"]:
            failed.append(
                "Config ``manifest.version`` should not contain ``dev`` for a release: "
                f"``{self.nf_config['manifest.version']}``"
            )
        else:
            passed.append(
                "Config ``manifest.version`` does not contain ``dev`` for release: "
                f"``{self.nf_config['manifest.version']}``"
            )

    if "custom_config" not in ignore_configs:
        # Check if custom profile params are set correctly
        if self.nf_config.get("params.custom_config_version", "").strip("'") == "master":
            passed.append("Config `params.custom_config_version` is set to `master`")
        else:
            failed.append("Config `params.custom_config_version` is not set to `master`")

        custom_config_base = "https://raw.githubusercontent.com/nf-core/configs/{}".format(
            self.nf_config.get("params.custom_config_version", "").strip("'")
        )
        if self.nf_config.get("params.custom_config_base", "").strip("'") == custom_config_base:
            passed.append(f"Config `params.custom_config_base` is set to `{custom_config_base}`")
        else:
            failed.append(f"Config `params.custom_config_base` is not set to `{custom_config_base}`")

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
        with open(path) as f:
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
                "Lines for loading custom profiles not found. File should contain: ```groovy\n{}".format(
                    "\n".join(lines)
                )
            )

    # Check for the availability of the "test" configuration profile by parsing nextflow.config
    with open(os.path.join(self.wf_path, "nextflow.config")) as f:
        content = f.read()

        # Remove comments
        cleaned_content = re.sub(r"//.*", "", content)
        cleaned_content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        match = re.search(r"\bprofiles\s*{", cleaned_content)
        if not match:
            failed.append("nextflow.config does not contain `profiles` scope, but `test` profile is required")
        else:
            # Extract profiles scope content and check for test profile
            start = match.end()
            end = start
            brace_count = 1
            while brace_count > 0 and end < len(content):
                if cleaned_content[end] == "{":
                    brace_count += 1
                elif cleaned_content[end] == "}":
                    brace_count -= 1
                end += 1
            profiles_content = cleaned_content[start : end - 1].strip()
            if re.search(r"\btest\s*{", profiles_content):
                passed.append("nextflow.config contains configuration profile `test`")
            else:
                failed.append("nextflow.config does not contain configuration profile `test`")

    # Check that the default values in nextflow.config match the default values defined in the nextflow_schema.json
    ignore_defaults = []
    for item in ignore_configs:
        if isinstance(item, dict) and "config_defaults" in item:
            ignore_defaults = item.get("config_defaults", [])
    schema_path = Path(self.wf_path) / "nextflow_schema.json"
    schema = PipelineSchema()
    schema.schema_filename = schema_path
    schema.no_prompts = True
    schema.load_schema()
    schema.get_schema_defaults()  # Get default values from schema
    schema.get_schema_types()  # Get types from schema
    for param_name in schema.schema_defaults.keys():
        param = "params." + param_name
        if param in ignore_defaults:
            ignored.append(f"Config default ignored: {param}")
        elif param in self.nf_config.keys():
            config_default = None
            schema_default = None
            if schema.schema_types[param_name] == "boolean":
                schema_default = str(schema.schema_defaults[param_name]).lower()
                config_default = str(self.nf_config[param]).lower()
            elif schema.schema_types[param_name] == "number":
                try:
                    schema_default = float(schema.schema_defaults[param_name])
                    config_default = float(self.nf_config[param])
                except ValueError:
                    failed.append(
                        f"Config default value incorrect: `{param}` is set as type `number` in nextflow_schema.json, but is not a number in `nextflow.config`."
                    )
            elif schema.schema_types[param_name] == "integer":
                try:
                    schema_default = int(schema.schema_defaults[param_name])
                    config_default = int(self.nf_config[param])
                except ValueError:
                    failed.append(
                        f"Config default value incorrect: `{param}` is set as type `integer` in nextflow_schema.json, but is not an integer in `nextflow.config`."
                    )
            else:
                schema_default = str(schema.schema_defaults[param_name])
                config_default = str(self.nf_config[param])
            if config_default is not None and config_default == schema_default:
                passed.append(f"Config default value correct: {param}= {schema_default}")
            else:
                failed.append(
                    f"Config default value incorrect: `{param}` is set as {self._wrap_quotes(schema_default)} in `nextflow_schema.json` but is {self._wrap_quotes(self.nf_config[param])} in `nextflow.config`."
                )
        else:
            failed.append(
                f"Default value from the Nextflow schema `{param} = {self._wrap_quotes(schema_default)}` not found in `nextflow.config`."
            )

    return {"passed": passed, "warned": warned, "failed": failed, "ignored": ignored}
