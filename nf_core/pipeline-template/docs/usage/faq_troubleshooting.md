# Frequently Asked Questions and Troubleshooting

<!-- TODO docs team: move most of these to central docs pages -->

## How do I update the pipeline to a more recent version?

See the nf-core documentation on <!-- TODO docs team: [updating pipelines](https://nf-co.re/docs/running/updating). -->

## How do I ensure reproducibility of my analysis?

The two primary ways to ensure reproducibility of your analysis are to always specify the pipeline version and to use parameter files.

- [**Pipeline versioning**](https://docs.seqera.io/nextflow/cli#revision-selection): explicitly declare using the Nextflow `-r` flag
- [**Parameter files**](https://docs.seqera.io/nextflow/cli#pipeline-parameters): use files that can be reused across runs, shared with others or uploaded as supplementary material for academic publications.

For more information see the documentation pages linked aobve.

## How do I resume a pipeline run?

Use the Nextflow [`-resume`](https://docs.seqera.io/nextflow/cache-and-resume) flag to resume a pipeline run.
This will re-run any failed or incomplete steps, and skip any steps that have already completed successfully.

### How can I use a different container to the one in the pipeline?

In some cases, you may wish to change the container or conda environment used by a pipeline steps for a particular tool (for example, if immediately need a newer version).

First ask the pipeline developer to update the tool and make a new release.
If you cannot wait, see the [updating tool versions](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#update-tool-versions) documentation.

### Custom Tool Arguments

A pipeline might not always support every possible argument or option of a particular tool used in pipeline.
Users can injected 'unspported' parameters that the pipeline does not include by default using a `ext.args` directive.

First ask the pipeline developer to add support for the tool arguments, and make a new release.
If you cannot wait, see the [modifying tool arguments](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#modifying-tool-arguments) documentation.

:::danger
Any injected parameters not natively supported by the pipeline may cause problems and break pipelines.
Using this method comes with no warranty or support from the developer.
:::
