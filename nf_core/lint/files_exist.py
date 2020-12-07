#!/usr/bin/env python

import os
import yaml


def files_exist(self):
    """Checks a given pipeline directory for required files.

    Iterates through the pipeline's directory content and checkmarks files
    for presence.

    Files that **must** be present::

        'nextflow.config',
        'nextflow_schema.json',
        ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md'], # NB: British / American spelling
        'README.md',
        'CHANGELOG.md',
        'docs/README.md',
        'docs/output.md',
        'docs/usage.md',
        '.github/workflows/branch.yml',
        '.github/workflows/ci.yml',
        '.github/workflows/linting.yml'

    Files that *should* be present::

        'main.nf',
        'environment.yml',
        'Dockerfile',
        'conf/base.config',
        '.github/workflows/awstest.yml',
        '.github/workflows/awsfulltest.yml'

    Files that *must not* be present::

        'Singularity',
        'parameters.settings.json',
        'bin/markdown_to_html.r',
        '.github/workflows/push_dockerhub.yml'

    Files that *should not* be present::

        '.travis.yml'

    Raises:
        An AssertionError if neither `nextflow.config` or `main.nf` found.
    """

    passed = []
    warned = []
    failed = []

    # NB: Should all be files, not directories
    # List of lists. Passes if any of the files in the sublist are found.
    files_fail = [
        ["nextflow.config"],
        ["nextflow_schema.json"],
        ["LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md"],  # NB: British / American spelling
        ["README.md"],
        ["CHANGELOG.md"],
        [os.path.join("docs", "README.md")],
        [os.path.join("docs", "output.md")],
        [os.path.join("docs", "usage.md")],
        [os.path.join(".github", "workflows", "branch.yml")],
        [os.path.join(".github", "workflows", "ci.yml")],
        [os.path.join(".github", "workflows", "linting.yml")],
    ]
    files_warn = [
        ["main.nf"],
        ["environment.yml"],
        ["Dockerfile"],
        [os.path.join("conf", "base.config")],
        [os.path.join(".github", "workflows", "awstest.yml")],
        [os.path.join(".github", "workflows", "awsfulltest.yml")],
    ]

    # List of strings. Dails / warns if any of the strings exist.
    files_fail_ifexists = [
        "Singularity",
        "parameters.settings.json",
        os.path.join("bin", "markdown_to_html.r"),
        os.path.join(".github", "workflows", "push_dockerhub.yml"),
    ]
    files_warn_ifexists = [".travis.yml"]

    # Remove files that should be ignored according to the linting config
    ignore_files = self.lint_config.get('files_exist', [])

    def pf(file_path):
        return os.path.join(self.wf_path, file_path)

    # First - critical files. Check that this is actually a Nextflow pipeline
    if not os.path.isfile(pf("nextflow.config")) and not os.path.isfile(pf("main.nf")):
        failed.append("File not found: nextflow.config or main.nf")
        raise AssertionError("Neither nextflow.config or main.nf found! Is this a Nextflow pipeline?")

    # Files that cause an error if they don't exist
    for files in files_fail:
        if any([f in ignore_files for f in files]):
            continue
        elif any([os.path.isfile(pf(f)) for f in files]):
            passed.append("File found: {}".format(self._wrap_quotes(files)))
        else:
            failed.append("File not found: {}".format(self._wrap_quotes(files)))

    # Files that cause a warning if they don't exist
    for files in files_warn:
        if any([f in ignore_files for f in files]):
            continue
        elif any([os.path.isfile(pf(f)) for f in files]):
            passed.append("File found: {}".format(self._wrap_quotes(files)))
        else:
            warned.append("File not found: {}".format(self._wrap_quotes(files)))

    # Files that cause an error if they exist
    for file in files_fail_ifexists:
        if file in ignore_files:
            continue
        if os.path.isfile(pf(file)):
            failed.append("File must be removed: {}".format(self._wrap_quotes(file)))
        else:
            passed.append("File not found check: {}".format(self._wrap_quotes(file)))

    # Files that cause a warning if they exist
    for file in files_warn_ifexists:
        if file in ignore_files:
            continue
        if os.path.isfile(pf(file)):
            warned.append("File should be removed: {}".format(self._wrap_quotes(file)))
        else:
            passed.append("File not found check: {}".format(self._wrap_quotes(file)))

    return {"passed": passed, "warned": warned, "failed": failed}
