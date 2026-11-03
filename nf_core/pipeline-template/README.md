{% if is_nfcore -%}

<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/images/{{ logo_dark }}">
    <img alt="{{ name }}" src="docs/images/{{ logo_light }}">
  </picture>
</h1>

{% else -%}

# {{ name }}

{% endif -%}
{% if github_badges -%}
{% if codespaces %}[![Open in GitHub Codespaces](https://img.shields.io/badge/Open_In_GitHub_Codespaces-black?labelColor=grey&logo=github)](https://github.com/codespaces/new/{{ name }}){% endif -%}
[![GitHub Actions CI Status](https://github.com/{{ name }}/actions/workflows/nf-test.yml/badge.svg)](https://github.com/{{ name }}/actions/workflows/nf-test.yml)
[![GitHub Actions Linting Status](https://github.com/{{ name }}/actions/workflows/linting.yml/badge.svg)](https://github.com/{{ name }}/actions/workflows/linting.yml){% endif -%}
{% if is_nfcore -%}[![AWS CI](https://img.shields.io/badge/CI%20tests-full%20size-FF9900?labelColor=000000&logo=Amazon%20AWS)](https://nf-co.re/{{ short_name }}/results){% endif -%}
{%- if github_badges -%}
[![Cite with Zenodo](http://img.shields.io/badge/DOI-10.5281/zenodo.XXXXXXX-1073c8?labelColor=000000)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![nf-test](https://img.shields.io/badge/unit_tests-nf--test-337ab7.svg)](https://www.nf-test.com)

[![Nextflow](https://img.shields.io/badge/version-%E2%89%A525.10.4-green?style=flat&logo=nextflow&logoColor=white&color=%230DC09D&link=https%3A%2F%2Fnextflow.io)](https://www.nextflow.io/)
[![nf-core template version](https://img.shields.io/badge/nf--core_template-{{ nf_core_version }}-green?style=flat&logo=nfcore&logoColor=white&color=%2324B064&link=https%3A%2F%2Fnf-co.re)](https://github.com/nf-core/tools/releases/tag/{{ nf_core_version }})
[![run with conda](http://img.shields.io/badge/run%20with-conda-3EB049?labelColor=000000&logo=anaconda)](https://docs.conda.io/en/latest/)
[![run with docker](https://img.shields.io/badge/run%20with-docker-0db7ed?labelColor=000000&logo=docker)](https://www.docker.com/)
[![run with singularity](https://img.shields.io/badge/run%20with-singularity-1d355c.svg?labelColor=000000)](https://sylabs.io/docs/)
[![Launch on Seqera Platform](https://img.shields.io/badge/Launch%20%F0%9F%9A%80-Seqera%20Platform-%234256e7)](https://cloud.seqera.io/launch?pipeline=https://github.com/{{ name }})

{% endif -%}
{%- if is_nfcore -%}[![Get help on Slack](http://img.shields.io/badge/slack-nf--core%20%23{{ short_name }}-4A154B?labelColor=000000&logo=slack)](https://nfcore.slack.com/channels/{{ short_name }}){% endif -%}
{%- if is_nfcore -%}[![Follow on Bluesky](https://img.shields.io/badge/bluesky-%40nf__core-1185fe?labelColor=000000&logo=bluesky)](https://bsky.app/profile/nf-co.re){% endif -%}
{%- if is_nfcore -%}[![Follow on Mastodon](https://img.shields.io/badge/mastodon-nf__core-6364ff?labelColor=FFFFFF&logo=mastodon)](https://mstdn.science/@nf_core){% endif -%}
{%- if is_nfcore -%}[![Watch on YouTube](http://img.shields.io/badge/youtube-nf--core-FF0000?labelColor=000000&logo=youtube)](https://www.youtube.com/c/nf-core)

{% endif -%}

## Introduction

**{{ name }}** is a bioinformatics pipeline that ...

<!-- TODO nf-core:
   Complete this sentence with a 2-3 sentence summary of what types of data the pipeline ingests, a brief overview of the
   major pipeline sections and the types of output it produces. You're giving an overview to someone new
   to nf-core here, in 15-20 seconds. For an example, see https://github.com/nf-core/rnaseq/blob/master/README.md#introduction
-->

<!-- TODO nf-core: Include a figure that guides the user through the major workflow steps. Many nf-core
     workflows use the "tube map" design for that. See https://nf-co.re/docs/community/brand/workflow-schematics#examples for examples.   -->

<!-- TODO nf-core: Fill in short bullet-pointed list of the default steps in the pipeline -->

{%- if fastqc %}1. Read QC ([`FastQC`](https://www.bioinformatics.babraham.ac.uk/projects/fastqc/)).{% endif -%}
{%- if multiqc %}2. Present QC for raw reads ([`MultiQC`](http://multiqc.info/)).{% endif -%}

## Usage

> [!NOTE]
> If you are new to Nextflow and nf-core, please refer to [this page](https://nf-co.re/docs/get_started/environment_setup/overview) on how to set-up Nextflow.

To run the pipeline:

- See the [usage](https://nf-co.re/{{ short_name }}/usage) documentation on how to prepare inputs.
- See the [parameter](https://nf-co.re/{{ short_name }}/parameters) documentation on how to configure run options.

Then run the following command:

<!-- TODO nf-core: update the following command to include all required parameters for a minimal example -->

```bash
nextflow run {{ name }} \
   -profile <docker/singularity/.../institute> \
   --input samplesheet.csv \
   --outdir <OUTDIR>
```

{% if is_nfcore -%}

{% if test_config %}

> [!NOTE]
> Want to [test your setup](https://nf-co.re/docs/get_started/run-your-first-pipeline) first?
> Run with `-profile test` before running the workflow on actual data.
> {% endif -%}

{% endif -%}

## Pipeline output

To familiarise yourself with what the pipeline produces:

- See the output of an example test run with a real dataset dataset on the [results](https://nf-co.re/{{ short_name }}/results) page.
- See the [output documentation](https://nf-co.re/{{ short_name }}/output) for detailed descriptions of pipeline outputs.

{% endif -%}

## Support and troubleshooting

If you have a question or hit an issue:

- See the relevant documentation on the relevant [pipeline documentation page](https://nf-co.re/{{ short_name }}/).
  {% if is_nfcore -%} - Ask on the nf-core [Slack `#{{ short_name }}` channel](https://nfcore.slack.com/channels/{{ short_name }}).

> [!NOTE]
> Not on the nf-core Slack?
> Join with [this invite](https://nf-co.re/join/slack)).

{% endif -%}

## Contributing and credits

To contribute to this pipeline:

- See the [contributing guidelines](docs/CONTRIBUTING.md).
  {% if is_nfcore -%}- See the ['how to contribute' guide](https://nf-co.re/docs/contributing/how-to-contribute){% endif -%}

{{ name }} was originally written by {{ author }}.

We thank the following people for their assistance in the development of this pipeline:

<!-- TODO nf-core: If applicable, make list of people who have also contributed -->

## Citations

<!-- TODO nf-core: Add citation for pipeline after first release. Uncomment lines below and update Zenodo doi and badge at the top of this file. -->
<!-- If you use {{ name }} for your analysis, please cite it using the following doi: [10.5281/zenodo.XXXXXX](https://doi.org/10.5281/zenodo.XXXXXX) -->

{% if citations %}
<!-- TODO nf-core: Add bibliography of tools and data used in your pipeline in CITATIONS file -->

References for the tools used by the pipeline can be found in the [`CITATIONS.md`](CITATIONS.md) file.
{%- endif -%}

This pipeline uses code and infrastructure developed and maintained by the [nf-core](https://nf-co.re) community, reused here under the [MIT license](https://github.com/nf-core/tools/blob/main/LICENSE).

{% if is_nfcore -%}
Cite the `nf-core` publications as follows:

{% else -%}

> **The nf-core framework for community-curated bioinformatics pipelines.**
>
> Philip Ewels, Alexander Peltzer, Sven Fillinger, Harshil Patel, Johannes Alneberg, Andreas Wilm, Maxime Ulysse Garcia, Paolo Di Tommaso & Sven Nahnsen.
>
> _Nat Biotechnol._ 2020 Feb 13. doi: [10.1038/s41587-020-0439-x](https://dx.doi.org/10.1038/s41587-020-0439-x).

> **Empowering bioinformatics communities with Nextflow and nf-core.**
> Björn Langer, et al.
>
> Langer, Björn E; Amaral, Andreia; Baudement, Marie-Odile; Bonath, Franziska; Charles, Mathieu; Chitneedi, Praveen Krishna; Clark, Emily L; Di Tommaso, Paolo; Djebali, Sarah; Ewels, Philip A; Eynard, Sonia; Fellows Yates, James A; Fischer, Daniel; Floden, Evan W; Foissac, Sylvain; Gabernet, Gisela; Garcia, Maxime U; Gillard, Gareth; Gundappa, Manu Kumar; Guyomar, Cervin; Hakkaart, Christopher; Hanssen, Friederike; Harrison, Peter W; Hörtenhuber, Matthias; Kurylo, Cyril; Kühn, Christa; Lagarrigue, Sandrine; Lallias, Delphine; Macqueen, Daniel J; Miller, Edmund; Mir-Pedrol, Júlia; Moreira, Gabriel Costa Monteiro; Nahnsen, Sven; Patel, Harshil; Peltzer, Alexander; Pitel, Frederique; Ramayo-Caldas, Yuliaxis; Ribeiro-Dantas, Marcel da Câmara; Rocha, Dominique; Salavati, Mazdak; Sokolov, Alexey; Espinosa-Carrasco, Jose; Notredame, Cedric; Community, The Nf-Core;
>
> _Genome Biology_, 2025 26(1), 228. doi: [10.1186/s13059-025-03673-9](https://doi.org/10.1186/s13059-025-03673-9)
