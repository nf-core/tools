import re
from pathlib import Path

from nf_core.utils import load_tools_config


def nf_test_content(self):
    """Checks that the pipeline nf-test files have the appropriate content.

    This lint test checks the following files and content of these files:

    * `*.nf.test` files should specify the `outdir` parameter:

        .. code-block:: yaml

            when {
                params {
                    outdir = "$outputDir"
                }
            }

    * A `versions.yml` file should be included in the snapshot of all `*.nf.test` files

    * The `nextflow.config` file should contain:
        .. code-block:: yaml
            modules_testdata_base_path = <path>

        .. code-block:: yaml
            pipelines_testdata_base_path = <path>

        And should set the correct resource limits, as defined in the `test` profile

    * The `nf-test.config` file should:
        * Make sure tests are relative to root directory

            .. code-block:: yaml

                testsDir "."

        * Ensure a user-configurable nf-test directory

            .. code-block:: yaml

                workDir System.getenv("NFT_WORKDIR") ?: ".nf-test"

        * Use a test specific config

            .. code-block:: yaml

                configFile "tests/nextflow.config"

    All these checks can be skipped in the `.nf-core.yml` file using:

        .. code-block:: yaml
            lint:
                nf_test_content: False

        or

        .. code-block:: yaml
            lint:
                nf_test_content:
                    - outdir
                    - versions.yml
                    - modules_testdata_base_path
                    - pipelines_testdata_base_path
                    - resourceLimits
                    - testsDir
                    - workDir
                    - configFile
    """
    passed = []
    failed = []
    ignored = []

    _, pipeline_conf = load_tools_config(self.wf_path)
    lint_conf = getattr(pipeline_conf, "lint", None) or None
    nf_test_content_conf = getattr(lint_conf, "nf_test_content", None) or []

    # Content of *.nf.test files
    test_fns = list(Path(self.wf_path, "tests").glob("*.nf.test"))
    outdir_pass = False
    versions_pass = False
    for test_fn in test_fns:
        with open(test_fn) as fh:
            for line in fh:
                # Check outdir is defined
                if "when" in line and "outdir" not in nf_test_content_conf:
                    while "}\n" not in line:
                        line = next(fh)
                        if re.search(r"outdir *= *[\"']\${?outputDir}?[\"']", line):
                            passed.append(f"'{test_fn}' contains `outdir` parameter")
                            outdir_pass = True
                            break
                # Check versions.yml is included in the snapshot
                if "versions.yml" in line and "versions.yml" not in nf_test_content_conf:
                    passed.append(f"'{test_fn}' snapshots a 'versions.yml' file")
                    versions_pass = True
        if not outdir_pass and "outdir" not in nf_test_content_conf:
            failed.append(
                f"""'{test_fn}' does not contain `outdir` parameter, it should contain `outdir = "$outputDir"`"""
            )
        elif "outdir" in nf_test_content_conf:
            ignored.append(f"'{test_fn}' checking `outdir` parameter ignored")
        if not versions_pass and "versions.yml" not in nf_test_content_conf:
            failed.append(f"'{test_fn}' snaphsots a 'versions.yml' file")
        elif "versions.yml" in nf_test_content_conf:
            ignored.append(f"'{test_fn}' checking `versions.yml` in snapshot ignored")

    # Content of nextflow.config file
    conf_fn = Path(self.wf_path, "tests", "nextflow.config")
    modules_testdata_base_path_pass = False
    pipelines_testdata_base_path_pass = False
    cpus_pass = False
    memory_pass = False
    time_pass = False

    with open(conf_fn) as fh:
        for line in fh:
            line = line.strip()
            if "modules_testdata_base_path" in line and "modules_testdata_base_path" not in nf_test_content_conf:
                passed.append(f"'{conf_fn}' contains `modules_testdata_base_path`")
                modules_testdata_base_path_pass = True
            if "pipelines_testdata_base_path" in line and "pipelines_testdata_base_path" not in nf_test_content_conf:
                passed.append(f"'{conf_fn}' contains `pipelines_testdata_base_path`")
                pipelines_testdata_base_path_pass = True
            if "resourceLimits" not in nf_test_content_conf:
                if "cpus" in line and "4" in line:
                    passed.append(f"'{conf_fn}' contains correct CPU resource limits")
                    cpus_pass = True
                if "memory" in line and "15.GB" in line:
                    passed.append(f"'{conf_fn}' contains correct memory resource limits")
                    memory_pass = True
                if "time" in line and "1.h" in line:
                    passed.append(f"'{conf_fn}' contains correct time resource limits")
                    time_pass = True

    if not modules_testdata_base_path_pass and "modules_testdata_base_path" in nf_test_content_conf:
        ignored.append(f"'{conf_fn}' checking `modules_testdata_base_path` ignored")
    else:
        failed.append(f"'{conf_fn}' does not contain `modules_testdata_base_path`")

    if not pipelines_testdata_base_path_pass and "pipelines_testdata_base_path" in nf_test_content_conf:
        ignored.append(f"'{conf_fn}' checking `pipelines_testdata_base_path` ignored")
    else:
        failed.append(f"'{conf_fn}' does not contain `pipelines_testdata_base_path`")

    if "resourceLimits" in nf_test_content_conf:
        ignored.append(f"'{conf_fn}' checking `resourceLimits` ignored")
    else:
        if not cpus_pass:
            failed.append(f"'{conf_fn}' does not contain correct CPU resource limits. Should be 4")
        if not memory_pass:
            failed.append(f"'{conf_fn}' does not contain correct memory resource limits. Should be 15.GB")
        if not time_pass:
            failed.append(f"'{conf_fn}' does not contain correct time resource limits. Should be 1.h")

    # Content of nf-test.config file
    nf_test_conf_fn = Path(self.wf_path, "nf-test.config")
    testsdir_pass = False
    workdir_pass = False
    configfile_pass = False
    with open(nf_test_conf_fn) as fh:
        for line in fh:
            if 'testsDir "."' in line and "testsDir" not in nf_test_content_conf:
                passed.append(f"'{nf_test_conf_fn}' sets a `testsDir`")
                testsdir_pass = True
            if 'workDir System.getenv("NFT_WORKDIR") ?: ".nf-test"' in line and "workDir" not in nf_test_content_conf:
                passed.append(f"'{nf_test_conf_fn}' sets a `workDir`")
                workdir_pass = True
            if 'configFile "tests/nextflow.config"' in line and "configFile" not in nf_test_content_conf:
                passed.append(f"'{nf_test_conf_fn}' sets a `configFile`")
                configfile_pass = True
    if not testsdir_pass and "testsDir" not in nf_test_content_conf:
        failed.append(f"""'{nf_test_conf_fn}' does not set a `testsDir`, it should contain `testsDir "."`""")
    elif "testsDir" in nf_test_content_conf:
        ignored.append(f"'{nf_test_conf_fn}' checking `testsDir` ignored")
    if not workdir_pass and "workDir" not in nf_test_content_conf:
        failed.append(
            f"""'{nf_test_conf_fn}' does not set a `workDir`, it should contain `workDir System.getenv("NFT_WORKDIR") ?: ".nf-test"`"""
        )
    elif "workDir" in nf_test_content_conf:
        ignored.append(f"'{nf_test_conf_fn}' checking `workDir` ignored")
    if not configfile_pass and "configFile" not in nf_test_content_conf:
        failed.append(
            f"""'{nf_test_conf_fn}' does not set a `configFile`, it should contain `configFile "tests/nextflow.config"`"""
        )
    elif "configFile" in nf_test_content_conf:
        ignored.append(f"'{nf_test_conf_fn}' checking `configFile` ignored")

    return {"passed": passed, "failed": failed, "ignored": ignored}
