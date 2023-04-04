{% if branded -%}

# ![{{ name }}](docs/images/{{ logo_light }}#gh-light-mode-only) ![{{ name }}](docs/images/{{ logo_dark }}#gh-dark-mode-only)

{% endif -%}
{% if gh_badges -%}
[![GitHub Actions CI Status](https://github.com/{{ name }}/workflows/nf-core%20CI/badge.svg)](https://github.com/{{ name }}/actions?query=workflow%3A%22nf-core+CI%22)
[![GitHub Actions Linting Status](https://github.com/{{ name }}/workflows/nf-core%20linting/badge.svg)](https://github.com/{{ name }}/actions?query=workflow%3A%22nf-core+linting%22){% endif -%}
{% if branded -%}[![AWS CI](https://img.shields.io/badge/CI%20tests-full%20size-FF9900?labelColor=000000&logo=Amazon%20AWS)](https://nf-co.re/{{ short_name }}/results){% endif -%}
{%- if github_badges -%}
[![Cite with Zenodo](http://img.shields.io/badge/DOI-10.5281/zenodo.XXXXXXX-1073c8?labelColor=000000)](https://doi.org/10.5281/zenodo.XXXXXXX)

[![Nextflow](https://img.shields.io/badge/nextflow%20DSL2-%E2%89%A522.10.1-23aa62.svg)](https://www.nextflow.io/)
[![run with conda](http://img.shields.io/badge/run%20with-conda-3EB049?labelColor=000000&logo=anaconda)](https://docs.conda.io/en/latest/)
[![run with docker](https://img.shields.io/badge/run%20with-docker-0db7ed?labelColor=000000&logo=docker)](https://www.docker.com/)
[![run with singularity](https://img.shields.io/badge/run%20with-singularity-1d355c.svg?labelColor=000000)](https://sylabs.io/docs/)
[![Launch on Nextflow Tower](https://img.shields.io/badge/Launch%20%F0%9F%9A%80-Nextflow%20Tower-%234256e7)](https://tower.nf/launch?pipeline=https://github.com/{{ name }})

{% endif -%}
{%- if branded -%}[![Get help on Slack](http://img.shields.io/badge/slack-nf--core%20%23{{ short_name }}-4A154B?labelColor=000000&logo=slack)](https://nfcore.slack.com/channels/{{ short_name }}){% endif -%}
{%- if branded -%}[![Follow on Twitter](http://img.shields.io/badge/twitter-%40nf__core-1DA1F2?labelColor=000000&logo=twitter)](https://twitter.com/nf_core){% endif -%}
{%- if branded -%}[![Watch on YouTube](http://img.shields.io/badge/youtube-nf--core-FF0000?labelColor=000000&logo=youtube)](https://www.youtube.com/c/nf-core)

{% endif -%}

## Introduction

<!-- TODO nf-core: Write a 2-3 sentence summary of what data the pipeline is for and what it does, e.g.

   > **nf-core/rnaseq** is a bioinformatics pipeline that can be used to analyse RNA sequencing data obtained from
   > organisms with a reference genome and annotation. It takes a samplesheet and FASTQ files as input,
   > performs quality control (QC), trimming and (pseudo-)alignment, and produces a gene expression matrix and extensive QC report.
-->

**{{ name }}** is a bioinformatics pipeline for {{ description }}.

<!-- TODO nf-core: Include a figure that guides the user through the major workflow steps. Many nf-core
     workflows use the "tube map" design for that. See https://nf-co.re/docs/contributing/design_guidelines#examples for examples.   -->
<!-- TODO nf-core: Fill in short bullet-pointed list of the default steps in the pipeline -->

1. Read QC ([`FastQC`](https://www.bioinformatics.babraham.ac.uk/projects/fastqc/))
2. Present QC for raw reads ([`MultiQC`](http://multiqc.info/))

## Usage

{% if branded -%}

> **Note**
> If you are new to nextflow and nf-core, please refer to [this page](https://nf-co.re/docs/usage/installation) on how
> to set-up nextflow. Make sure to [test your setup](https://nf-co.re/docs/usage/introduction#how-to-run-a-pipeline)
> with `-profile test` before running the workflow on actual data.

{% endif -%}

<!-- TODO nf-core: Describe the minimum required steps to execute the pipeline, e.g. how to prepare samplesheets.
     Explain what rows and columns represent.
 -->

First, you need to prepare a samplesheet with your input data that looks as follows:

**samplesheet.csv**:

```csv
sample,fastq_1,fastq_2
CONTROL_REP1,AEG588A1_S1_L002_R1_001.fastq.gz,AEG588A1_S1_L002_R2_001.fastq.gz
```

Each row represents a fastq file (single-end) or a pair of fastq files (paired end).

> **Warning**
> Please provide pipeline parameters via the CLI or Nextflow `-params-file` option. Custom config files including those
> provided by the `-c` Nextflow option can be used to provide any configuration **except for parameters**;
> see [docs](https://nf-co.re/usage/configuration#custom-configuration-files).

Now, you can run the pipeline using:

<!-- TODO nf-core: update the following command to include all required parameters for a minimal example -->

```bash
nextflow run {{ name }} \
   --input samplesheet.csv \
   -profile <docker/singularity/.../institute>
```

{% if branded -%}

For more details, please refer to the [usage documentation](https://nf-co.re/{{ short_name }}/usage) and the [parameter documentation](https://nf-co.re/{{ short_name }}/parameters).

{% endif -%}

{% if branded -%}

## Pipeline output

<!-- TODO nf-core: if your pipeline comes with a full-sized test dataset, add a sentence linking to the dataset and https://nf-co.re/{{ short_name }}/results. -->

For more details, please refer to the [output documentation](https://nf-co.re/{{ short_name }}/output).

{% endif -%}

## Credits

{{ name }} was originally written by {{ author }}.

We thank the following people for their extensive assistance in the development of this pipeline:

<!-- TODO nf-core: If applicable, make list of people who have also contributed -->

## Contributions and Support

If you would like to contribute to this pipeline, please see the [contributing guidelines](.github/CONTRIBUTING.md).

{% if branded -%}
For further information or help, don't hesitate to get in touch on the [Slack `#{{ short_name }}` channel](https://nfcore.slack.com/channels/{{ short_name }}) (you can join with [this invite](https://nf-co.re/join/slack)).

{% endif -%}

## Citations

<!-- TODO nf-core: Add citation for pipeline after first release. Uncomment lines below and update Zenodo doi and badge at the top of this file. -->
<!-- If you use  {{ name }} for your analysis, please cite it using the following doi: [10.5281/zenodo.XXXXXX](https://doi.org/10.5281/zenodo.XXXXXX) -->

<!-- TODO nf-core: Add bibliography of tools and data used in your pipeline -->

An extensive list of references for the tools used by the pipeline can be found in the [`CITATIONS.md`](CITATIONS.md) file.

{% if branded -%}
You can cite the `nf-core` publication as follows:

{% else -%}
This pipeline uses code and infrastructure developed and maintained by the [nf-core](https://nf-co.re) community, reused here under the [MIT license](https://github.com/nf-core/tools/blob/master/LICENSE).

{% endif -%}

> **The nf-core framework for community-curated bioinformatics pipelines.**
>
> Philip Ewels, Alexander Peltzer, Sven Fillinger, Harshil Patel, Johannes Alneberg, Andreas Wilm, Maxime Ulysse Garcia, Paolo Di Tommaso & Sven Nahnsen.
>
> _Nat Biotechnol._ 2020 Feb 13. doi: [10.1038/s41587-020-0439-x](https://dx.doi.org/10.1038/s41587-020-0439-x).
