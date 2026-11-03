# Required computing resources

In this page we provide information and guidance on how nf-core/mag works by default, and in some cases how to optimise computational resource usage.

## Default resource requests

The following table lists the default resources that Nextflow will request from a machine on it's first execution attempt for a given module.

The source information for this table is from files in the code base.

:::note
If you want to see the source information, look in `conf/base.conf` and the module files themselves `modules/*/<module_name>/main.nf`.
:::

To customise these resource requests away from the tables, see the central [nf-core instructions](https://nf-co.re/docs/running/configuration/nextflow-for-your-system#customize-process-resources).

Please also note the following:

- Not all modules in this table will run in every pipeline run, nor will the tool necessarily _use_ the requested amount.
- On certain module execution failures (such as out of memory), Nextflow will try and resubmit with increased resources with the equation `<resource value> * task.attempt`, up to a certain number of retries. See `conf/base.conf` for more information.

The table is ordered first by 'Source' of defaults by specificity of definition, then by 'memory', and then 'Module name' by alphabetical order.

<!-- TODO nf-core: update this table when new modules added/defaults changed, if using an LLM, careful to tell it to follow module import aliases -->

| Module Name        | CPU | Memory | Time | Source                         |
| ------------------ | --- | ------ | ---- | ------------------------------ |
| GTDBTK_CLASSIFYWF  | 10  | 140.GB | 12.h | Named customisation            |
| COMEBIN_RUNCOMEBIN | 12  | 72.GB  | 16.h | Module label: `process_high`   |
| ADAPTERREMOVAL     | 6   | 36.GB  | 8.h  | Module label: `process_medium` |
| FASTQC             | 2   | 12.GB  | 4.h  | Module label: `process_low`    |
| CAT_FASTQ          | 1   | 6.GB   | 4.h  | Module label: `process_single` |
| BIN_SUMMARY        | 1   | 7.GB   | 4.h  | Pipeline fallback default      |

:::note{title="Table legend: source column"}

- Name customisation: resource request defined specifically for this module using `withName:` directive in a configuration file.
- Label: process_high/medium/low/single: resource request defined with a common label `withLabel:` directive in a configuration file.
- Pipeline fallback default: resource request defined in the pipeline configuration file as a fallback default with no specific directive.
  :::
