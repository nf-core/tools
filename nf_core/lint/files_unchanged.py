#!/usr/bin/env python

import filecmp
import logging
import os
import shutil
import tempfile

import nf_core.create


def files_unchanged(self):
    """Checks that certain pipeline files are not modified from template output.

    Iterates through the pipeline's directory content and compares specified files
    against output from the template using the pipeline's metadata. File content
    should not be modified / missing.

    Files that must be unchanged::

        .gitattributes
        .markdownlint.yml
        .github/.dockstore.yml
        .github/CONTRIBUTING.md
        .github/ISSUE_TEMPLATE/bug_report.md
        .github/ISSUE_TEMPLATE/config.yml
        .github/ISSUE_TEMPLATE/feature_request.md
        .github/PULL_REQUEST_TEMPLATE.md
        .github/workflows/branch.yml
        .github/workflows/linting_comment.yml
        .github/workflows/linting.yml
        assets/email_template.html
        assets/email_template.txt
        assets/nf-core-PIPELINE_logo.png
        assets/sendmail_template.txt
        CODE_OF_CONDUCT.md
        docs/images/nf-core-PIPELINE_logo.png
        docs/README.md'
        lib/nfcore_external_java_deps.jar
        lib/NfcoreSchema.groovy
        lib/NfcoreTemplate.groovy
        ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md'], # NB: British / American spelling

    Files that can have additional content but must include the template contents::

        .gitignore
        assets/multiqc_config.yaml

    .. tip:: You can configure the ``nf-core lint`` tests to ignore any of these checks by setting
             the ``files_unchanged`` key as follows in your linting config file. For example:

             .. code-block:: yaml

                files_unchanged:
                  - .github/workflows/branch.yml
                  - assets/multiqc_config.yaml

    """

    passed = []
    failed = []
    ignored = []
    fixed = []
    could_fix = False

    # Check that we have the minimum required config
    try:
        self.nf_config["manifest.name"]
        self.nf_config["manifest.description"]
        self.nf_config["manifest.author"]
    except KeyError as e:
        return {"ignored": [f"Required pipeline config not found - {e}"]}
    short_name = self.nf_config["manifest.name"].strip("\"'").replace("nf-core/", "")

    # NB: Should all be files, not directories
    # List of lists. Passes if any of the files in the sublist are found.
    files_exact = [
        [".gitattributes"],
        [".markdownlint.yml"],
        ["CODE_OF_CONDUCT.md"],
        ["LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md"],  # NB: British / American spelling
        [os.path.join(".github", ".dockstore.yml")],
        [os.path.join(".github", "CONTRIBUTING.md")],
        [os.path.join(".github", "ISSUE_TEMPLATE", "bug_report.md")],
        [os.path.join(".github", "ISSUE_TEMPLATE", "config.yml")],
        [os.path.join(".github", "ISSUE_TEMPLATE", "feature_request.md")],
        [os.path.join(".github", "PULL_REQUEST_TEMPLATE.md")],
        [os.path.join(".github", "workflows", "branch.yml")],
        [os.path.join(".github", "workflows", "linting_comment.yml")],
        [os.path.join(".github", "workflows", "linting.yml")],
        [os.path.join("assets", "email_template.html")],
        [os.path.join("assets", "email_template.txt")],
        [os.path.join("assets", "sendmail_template.txt")],
        [os.path.join("assets", f"nf-core-{short_name}_logo.png")],
        [os.path.join("bin", "scrape_software_versions.py")],
        [os.path.join("docs", "images", f"nf-core-{short_name}_logo.png")],
        [os.path.join("docs", "README.md")],
        [os.path.join("lib", "nfcore_external_java_deps.jar")],
        [os.path.join("lib", "NfcoreSchema.groovy")],
        [os.path.join("lib", "NfcoreTemplate.groovy")],
    ]
    files_partial = [
        [".gitignore", "foo"],
        [os.path.join("assets", "multiqc_config.yaml")],
    ]

    # Only show error messages from pipeline creation
    logging.getLogger("nf_core.create").setLevel(logging.ERROR)

    # Generate a new pipeline with nf-core create that we can compare to
    test_pipeline_dir = os.path.join(tempfile.mkdtemp(), "nf-core-{}".format(short_name))
    create_obj = nf_core.create.PipelineCreate(
        self.nf_config["manifest.name"].strip("\"'"),
        self.nf_config["manifest.description"].strip("\"'"),
        self.nf_config["manifest.author"].strip("\"'"),
        outdir=test_pipeline_dir,
    )
    create_obj.init_pipeline()

    # Helper functions for file paths
    def _pf(file_path):
        """Helper function - get file path for pipeline file"""
        return os.path.join(self.wf_path, file_path)

    def _tf(file_path):
        """Helper function - get file path for template file"""
        return os.path.join(test_pipeline_dir, file_path)

    # Files that must be completely unchanged from template
    for files in files_exact:

        # Ignore if file specified in linting config
        ignore_files = self.lint_config.get("files_unchanged", [])
        if any([f in ignore_files for f in files]):
            ignored.append("File ignored due to lint config: {}".format(self._wrap_quotes(files)))

        # Ignore if we can't find the file
        elif not any([os.path.isfile(_pf(f)) for f in files]):
            ignored.append("File does not exist: {}".format(self._wrap_quotes(files)))

        # Check that the file has an identical match
        else:
            for f in files:
                try:
                    if filecmp.cmp(_pf(f), _tf(f), shallow=True):
                        passed.append(f"`{f}` matches the template")
                    else:
                        if "files_unchanged" in self.fix:
                            # Try to fix the problem by overwriting the pipeline file
                            shutil.copy(_tf(f), _pf(f))
                            passed.append(f"`{f}` matches the template")
                            fixed.append(f"`{f}` overwritten with template file")
                        else:
                            failed.append(f"`{f}` does not match the template")
                            could_fix = True
                except FileNotFoundError:
                    pass

    # Files that can be added to, but that must contain the template contents
    for files in files_partial:

        # Ignore if file specified in linting config
        ignore_files = self.lint_config.get("files_unchanged", [])
        if any([f in ignore_files for f in files]):
            ignored.append("File ignored due to lint config: {}".format(self._wrap_quotes(files)))

        # Ignore if we can't find the file
        elif not any([os.path.isfile(_pf(f)) for f in files]):
            ignored.append("File does not exist: {}".format(self._wrap_quotes(files)))

        # Check that the file contains the template file contents
        else:
            for f in files:
                try:
                    with open(_pf(f), "r") as fh:
                        pipeline_file = fh.read()
                    with open(_tf(f), "r") as fh:
                        template_file = fh.read()
                    if template_file in pipeline_file:
                        passed.append(f"`{f}` matches the template")
                    else:
                        if "files_unchanged" in self.fix:
                            # Try to fix the problem by overwriting the pipeline file
                            with open(_tf(f), "r") as fh:
                                template_file = fh.read()
                            with open(_pf(f), "w") as fh:
                                fh.write(template_file)
                            passed.append(f"`{f}` matches the template")
                            fixed.append(f"`{f}` overwritten with template file")
                        else:
                            failed.append(f"`{f}` does not match the template")
                            could_fix = True
                except FileNotFoundError:
                    pass

    return {"passed": passed, "failed": failed, "ignored": ignored, "fixed": fixed, "could_fix": could_fix}
