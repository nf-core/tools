<!--
# {{ name }} pull request

Many thanks for contributing to {{ name }}!

Please fill in the appropriate checklist below (delete whatever is not relevant).
These are the most common things requested on pull requests (PRs).

Remember that PRs should be made against the dev branch, unless you're preparing a pipeline release.

Learn more about contributing: [CONTRIBUTING.md](https://github.com/{{ name }}/tree/{{ default_branch }}/.github/CONTRIBUTING.md)
-->

## PR checklist

- [ ] This comment contains a description of changes (with reason).
- [ ] If you've fixed a bug or added code that should be tested, add tests!
- [ ] If you've added a new tool - have you followed the pipeline conventions in the [contribution docs](https://github.com/{{ name }}/tree/{{ default_branch }}/.github/CONTRIBUTING.md)
      {%- if is_nfcore %}
- [ ] If necessary, also make a PR on the {{ name }} _branch_ on the [nf-core/test-datasets](https://github.com/nf-core/test-datasets) repository.
      {%- endif %}
- [ ] Make sure your code lints (`nf-core pipelines lint`).
      {%- if test_config %}
- [ ] Ensure the test suite passes (`nextflow run . -profile test,docker --outdir <OUTDIR>`).
- [ ] Check for unexpected warnings in debug mode (`nextflow run . -profile debug,test,docker --outdir <OUTDIR>`).
      {%- endif %}
- [ ] Usage Documentation in `docs/usage.md` is updated.
- [ ] Output Documentation in `docs/output.md` is updated.
- [ ] `CHANGELOG.md` is updated.
- [ ] `README.md` is updated (including new tool citations and authors/contributors).
