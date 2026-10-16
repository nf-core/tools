# {{ name }}: Usage

{% if is_nfcore -%}

## :warning: Please read this documentation on the nf-core website: [https://nf-co.re/{{ short_name }}/usage](https://nf-co.re/{{ short_name }}/usage)

{% endif -%}

> _Documentation of pipeline parameters is generated automatically from the pipeline schema and can no longer be found in markdown files._

## Introduction

**{{ name }}** is a bioinformatics pipeline that ...

<!-- TODO nf-core:
   Complete this section with a 2-3 paragraph extended summary of what types of data the pipeline ingests, a brief overview of the major pipeline sections and the types of output it produces.

   This can be copied from the README.md, but here provide more detailed (scientific) context and rationale behind the pipeline on why it is useful to the community.
-->

<!-- TODO nf-core: Fill in short bullet-pointed list of the default steps in the pipeline. Can be copied from the main README. -->

This pipeline performs:

{%- if fastqc %}1. Read QC ([`FastQC`](https://www.bioinformatics.babraham.ac.uk/projects/fastqc/)).{% endif %}
{%- if multiqc %}2. Present QC for raw reads ([`MultiQC`](http://multiqc.info/)).{% endif %}

## Prequisites

### Dependencies

To run this pipeline, you will need installed, at a minimum:

- Nextflow
- A container or software management system (Docker, Apptainer, Conda etc.).

For more information on how to prepare your environment please see the [nf-core environment setup page](https://nf-co.re/docs/get_started/environment_setup/overview).

### Computing resources

The memory requirements for Nextflow itself is quite low.
In some cases when running many jobs, you may need more moment.
If you find Nextflow itself hits out of memory errors, see the [nf-core documentation](<!-- TODO: docs team -->) on how to adjust.

The tools in each step of the pipeline will require different amounts of memory and CPU resources.
The default resource requests for each pipeline step can be seen in [compute resource guidance](compute_resource_guidance.md).

If you find the defaults are over- or under-requesting compute resources, adjust the resources for a particular step using as documented in [Infrastructure configuration](#infrastructure-configuration)

### Infrastructure configuration

To configure Nextflow to execute on your machine or computing infrastructure, you may additionally need to use a configuration file for configuring memory, CPUs, and other resources.
See [nf-core/configs](https://nf-co.re/configs) for a list of pre-made configuration files for various institutional HPCs and other computing infrastructures.

For more information on how to configure Nextflow for your system, please see the [nf-core configuration options page](https://nf-co.re/docs/running/configuration/configuration-options).

## Preparing your pipeline run

### Samplesheet inputs

nf-core pipelines use 'samplesheets' to specify the location of input files and metadata for each sample.
The input samplesheets are typically comma-separated-value (`.csv`) files and are supplied to the `--input` parameter.

```bash
--input '<path to samplesheet file>'
```

An example of a minimal samplesheet for the `--input` of {{ name }} can be seen below.

<!-- TODO nf-core: update this samplesheet to match your pipeline -->

```csv title="samplesheet.csv"
sample,fastq_1,fastq_2
CONTROL_REP1,AEG588A1_S1_L002_R1_001.fastq.gz,AEG588A1_S1_L002_R2_001.fastq.gz
CONTROL_REP1,AEG588A1_S1_L003_R1_001.fastq.gz,AEG588A1_S1_L003_R2_001.fastq.gz
CONTROL_REP1,AEG588A1_S1_L004_R1_001.fastq.gz,AEG588A1_S1_L004_R2_001.fastq.gz
```

Each column in the samplesheet have requirements on the contents and how they should be formatted. The table below describes the requirements for each column in the samplesheet.

<!-- TODO nf-core: update this table to match your pipeline -->

| Column    | Description                                                                                                                                                                            |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sample`  | Custom sample name. This entry will be identical for multiple sequencing libraries/runs from the same sample. Spaces in sample names are automatically converted to underscores (`_`). |
| `fastq_1` | Full path to FastQ file for Illumina short reads 1. File has to be gzipped and have the extension ".fastq.gz" or ".fq.gz".                                                             |
| `fastq_2` | Full path to FastQ file for Illumina short reads 2. File has to be gzipped and have the extension ".fastq.gz" or ".fq.gz".                                                             |

A full realistic example of a samplesheet for {{ name }} is as follows.

<!-- TODO nf-core: update this csv to match your pipeline -->

```csv title="samplesheet.csv"
sample,fastq_1,fastq_2
CONTROL_REP1,AEG588A1_S1_L002_R1_001.fastq.gz,AEG588A1_S1_L002_R2_001.fastq.gz
CONTROL_REP2,AEG588A2_S2_L002_R1_001.fastq.gz,AEG588A2_S2_L002_R2_001.fastq.gz
CONTROL_REP3,AEG588A3_S3_L002_R1_001.fastq.gz,AEG588A3_S3_L002_R2_001.fastq.gz
TREATMENT_REP1,AEG588A4_S4_L003_R1_001.fastq.gz,
TREATMENT_REP2,AEG588A5_S5_L003_R1_001.fastq.gz,
TREATMENT_REP3,AEG588A6_S6_L003_R1_001.fastq.gz,
TREATMENT_REP3,AEG588A6_S6_L004_R1_001.fastq.gz,
```

<!-- TODO nf-core: update the example samplesheet in assets/ to match your pipeline  -->

An [example samplesheet](../assets/samplesheet.csv) has also been provided with the pipeline.

### Preparing parameters

nf-core pipelines offer a number of parameters to control the behaviour and tune the execution of each step of the pipeline.

To see all the available parameters for the pipeline, {% if is_nfcore -%}please see the [parameters documentation](https://nf-co.re/{{ short_name }}/parameters) on the nf-core website or{% endif -%} run `nextflow run {{ name }} --help` on the command line.

Adjust pipeline parameters with either:

- Command-line arguments
- Parameter files {% if is_nfcore -%}(You can also generate such `YAML`/`JSON` files with [nf-core/launch](https://nf-co.re/launch)).{% endif -%}

To learn more about the differences, see the [nf-core documentation](https://nf-co.re/docs/running/run-pipelines#running-with-your-own-data).

> [! TIP]
> nf-core recommends using params files for ensuring reproducbility of your analysis.

> [!WARNING]
> Do not use `-c <file>` to specify parameters as this will result in errors. Custom config files specified with `-c` must only be used for [tuning process resource specifications](https://nf-co.re/docs/running/run-pipelines#configuring-pipelines), other infrastructural tweaks (such as output directories), or module arguments (args).

## Running the pipeline

The typical command for running the pipeline is as follows:

```bash
nextflow run {{ name }} -r <pipeline version> --input ./samplesheet.csv --outdir ./results -profile docker <pipeline parameters>
```

This example will launch the pipeline with the `docker` configuration profile.
See below for more information about profiles.

> [! TIP]
> nf-core recommend always specifying the pipeline version with `-r <pipeline version>` to ensure reproducibility of your analysis.

## Pipeline run output

The pipeline will create the following directories and files in the directory you executed the run:

```bash
<execution directory>
├── .nextflow
├── .nextflow.log
├── results/
└── work/
```

The output files from the pipeline itself will be stored under the location specified under `--outdir` in your command line.
For detailed descriptions of the pipeline outputs in `--outdir`, see {% if is_nfcore -%}[output documentation](https://nf-co.re/{{ short_name }}/output){% endif -%} or [output.md](output.md).

The primary pipeline execution log is stored in the hidden `.nextflow.log` file.
Internal run intermediate files useful for debugging runs are stored under `work/`.

Other Nextflow run internal files are stored under `.nextflow/`.

<!-- TODO JAMES UP TO HERE -->

## Troubleshooting and other frequently asked questions

If you encounter any problems running the pipeline, please see the [troubleshooting documentation](faq_troubleshooting.md) for help.

{% if is_nfcore -%}
If after reviewing the documentation, your problem is still unresolved, please post a message to the [nf-core Slack](https://nfcore.slack.com/) (you can sign up for an invite [here](https://nfcore.slack.com/join/shared_invite/zt-1f4x0g7k9-
{% endif -%}
