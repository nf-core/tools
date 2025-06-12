# genomic-medicine-sweden/metaval: Usage

> _Documentation of pipeline parameters is generated automatically from the pipeline schema and can no longer be found in markdown files._

## Introduction

**genomic-medicine-sweden/metaval** is a bioinformatics pipeline for post-processing of [nf-core/taxprofiler](https://github.com/nf-core/taxprofiler) results. It verifies the classification results by the nf-core/taxprofiler pipeline. At the moment, `genomic-medicine-sweden/metaval` only verifies the classification results from three classifiers `Kraken2`, `Centrifuge` and `diamond`.

The pipeline, constructed using the `nf-core` [template](https://nf-co.re/tools#creating-a-new-pipeline), utilizing Docker/Singularity containers for easy installation and reproducible results. The implementation follows [Nextflow DSL2](https://www.nextflow.io/docs/latest/dsl1.html), employing one container per process for simplified maintenance and dependency management. Processes are sourced from [nf-core/modules](https://github.com/nf-core/modules) for broader accessibility within the Nextflow community.

<!-- TODO nf-core: Add documentation about anything specific to running your pipeline. For general topics, please point to (and add to) the main nf-core website. -->

## Prerequisites

1. Install Nextflow (>=23.04.0) using the instructions [here.](https://nextflow.io/docs/latest/getstarted.html#installation)
2. Install one of the following technologies for full pipeline reproducibility: Docker, Singularity, Podman, Shifter or Charliecloud.

## Input

### Samplesheet

You will need to create a samplesheet in csv format with information about the samples you would like to analyse before running the pipeline. It has to be a comma-separated file and a header row as shown in the examples below.

```bash
--input '[path to samplesheet file]'
```

genomic-medicine-sweden/metaval will require the information given bellow.

| Column              | Description                                                                                                                                      |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| sample              | Unique sample name [required].                                                                                                                   |
| run_accession       | Run ID or name unique for each (pairs of) file(s). Can also supply sample name again here, if only a single run was generated [required].        |
| instrument_platform | Sequencing platform reads generated on, selected from the EBI ENA controlled vocabulary [required].                                              |
| fastq_1             | Unmapped human reads from bowtie2/minimap2, filtered reads from bbduk/nanoq/FiltLong or raw sequencing reads. Gzipped compressed files accepted. |
| fastq_2             | Unmapped human reads from bowtie2, filtered reads from bbduk/nanoq/FiltLong or raw reads. Gzipped compressed files accepted.                     |
| kraken2_report      | Kraken2 report containing stats about classified and not classified reads.                                                                       |
| kraken2_result      | Kraken2 output file indicating the taxonomic assignment of each input read.                                                                      |
| kraken2_taxpasta    | Standardized kraken2 taxonomic profiles for all samples.                                                                                         |
| centrifuge_report   | File containing kraken-style report from centrifuge output files.                                                                                |
| centrifuge_result   | File containing classification results.                                                                                                          |
| centrifuge_taxpasta | Standardized centrifuge taxonomic profiles for all samples.                                                                                      |
| diamond             | Tab-separated file containing taxonomic classification of hits.                                                                                  |
| diamond_taxpasta    | Standardized diamond taxonomic profiles for all samples.                                                                                         |

```csv title="samplesheet.csv"
sample,run_accession,instrument_platform,fastq_1,fastq_2,kraken2_report,kraken2_result,kraken2_taxpasta,centrifuge_report,centrifuge_result,centrifuge_taxpasta,diamond,diamond_taxpasta
sample1,run1,ILLUMINA,sample1.unmapped_1.fastq.gz,sample1.unmapped_2.fastq.gz,sample1.kraken2.kraken2.report.txt,sample1.kraken2.kraken2.classifiedreads.txt,kraken2_kraken2-db.tsv,sample1.centrifuge.txt,sample1.centrifuge.results.txt,centrifuge_centrifuge-db.tsv,sample1.diamond.tsv,diamond_diamond-db.tsv
sample2,run1,ILLUMINA,sample2.unmapped_1.fastq.gz,sample2.unmapped_2.fastq.gz,sample2.kraken2.kraken2.report.txt,sample2.kraken2.kraken2.classifiedreads.txt,kraken2_kraken2-db.tsv,sample2.centrifuge.txt,sample2.centrifuge.results.txt,centrifuge_centrifuge-db.tsv,sample2.diamond.tsv,diamond_diamond-db.tsv
```

### Optional input

#### Pathogen genome database

A concatenated FASTA file containing all the pathogen genomes a user is interested in.

#### accession2taxid

Users need to prepare a file containing accession IDs of pathogens and their corresponding taxonomic IDs

#### Blastn and/or Blastn database

Use a custom database or download available [NCBI databases](https://ftp.ncbi.nlm.nih.gov/blast/db/). See the [documentation](https://ftp.ncbi.nlm.nih.gov/blast/documents/blastdb.html). To speed up the BLAST process, be cautious with which the choice of database. For example, for viruses, one could use `ref_viruses_rep_genomes` or `refseq_protein` instead of the `nt` or `nr` database.

## Running the pipeline

The example commands for running each workflow are as follows:

```bash
# Green Workflow - pathogen screening
nextflow run genomic-medicine-sweden/metaval --input ./samplesheet.csv --outdir ./results -profile docker --perform_screen_pathogens --pathogens_genomes /path/to/reference.fna --accession2taxid /path/to/accession2taxid.map

# Orange Workflow - Verify Identified Viruses
nextflow run genomic-medicine-sweden/metaval --input ./samplesheet.csv --outdir ./results -profile docker --perform_extract_reads --extract_kraken2_reads --extract_centrifuge_reads --extract_diamond_reads

# Blue Workflow - Verify User-Defined TaxIDs
nextflow run genomic-medicine-sweden/metaval --input ./samplesheet.csv --outdir ./results -profile docker --taxid 211044 2886042 --perform_extract_reads --extract_kraken2_reads --extract_centrifuge_reads --extract_diamond_reads

```

This will launch the pipeline with the `docker` configuration profile. See below for more information about profiles.

Note that the pipeline will create the following files in your working directory:

```bash
work                # Directory containing the nextflow working files
<OUTDIR>            # Finished results in specified location (defined with --outdir)
.nextflow_log       # Log file from Nextflow
# Other nextflow hidden files, eg. history of pipeline runs and old logs.
```

If you wish to repeatedly use the same parameters for multiple runs, rather than specifying each flag in the command, you can specify these in a params file.

Pipeline settings can be provided in a `yaml` or `json` file via `-params-file <file>`.

> [!WARNING]
> Do not use `-c <file>` to specify parameters as this will result in errors. Custom config files specified with `-c` must only be used for [tuning process resource specifications](https://nf-co.re/docs/usage/configuration#tuning-workflow-resources), other infrastructural tweaks (such as output directories), or module arguments (args).

The above pipeline run specified with a params file in yaml format:

```bash
nextflow run genomic-medicine-sweden/metaval -profile docker -params-file params.yaml
```

with:

```yaml title="params.yaml"
input: './samplesheet.csv'
outdir: './results/'
genome: 'GRCh37'
<...>
```

You can also generate such `YAML`/`JSON` files via [nf-core/launch](https://nf-co.re/launch).

### Decontamination

Filtering the output files from metagenomics classifiers like `Kraken2`, `Centrifuge`, or `DIAMOND` to remove false positives and background contamination can be activated by enabling `--decontamination` option. This step compares results to the negative control to identify likely present species based on user-defined thresholds.

### Extract Viral TaxIDs

This step involves extracting all taxonomic IDs of viral species predicted by classifiers by enabling `--perform_extract_reads`and the `--taxid` should be empty.

### Extract Reads

This step either retrieves the reads of all viral TaxIDs predicted by classifiers or extracts reads from a user-defined list of TaxIDs separated by spaces when the `--taxid` option is activated. Extracting reads predicted by `Kraken2` can be activated with `--extract_kraken2_reads`, extracting reads predicted by `Centrifuge` can be activated with `--extract_centrifuge_reads` and extracting reads predicted by `DIAMOND` can be activated with `--extract_diamond_reads`.

If the `--taxid` option is included in the command line, the pipeline will only extract reads for the user specified TaxIDs, in other words, `--taxid` takes priority.

### de-novo assembly

De-novo assembly can be performed for extracted reads of TaxIDs by enabling `--perform_shortread_denovo` for short reads or the `--perform_longread_denovo` option for long reads, provided the number of reads exceeds `params.min_read_counts`. The recommended minimum number of reads is 100. If there are too few reads, the process will fail.

### Mapping

To screen for the existence of pathogens in samples, map the raw reads to a pathogens genome database (`--pathogens_genomes`) by activating the `--perform_screen_pathogens` option. Alternatively, map the extract reads of taxIDs to the genomes that correspond to the positive hits from BLASTx/BLASTn.

Use `Bowtie2` for short reads and `minimap2` for long reads.

### Call consensus

Consensus sequence calling from reads mapped to pathogen genomes can be performed by turning on the option `--perform_screen_pathogens` and either `--perform_shortread_consensus` or `--perform_longread_consensus`. For Illumina reads, `samtools consensus` is used. For Nanopore reads, either `samtools consensus` or `medaka_consensus` (defined by `params.longread_consensus_tool`) can be used. `medaka` is specifically designed for Nanopore reads and utilizes a neural network to improve consensus accuracy, whereas `samtools consensus` does not have a specialized algorithm for Nanopore data. Therefore, `medaka` is generally recommended for Nanopore reads.

It’s recommended to enable consensus calling if the number of reads mapped to pathogen genomes exceeds `params.min_read_counts`, with a minimum of 100 reads. Too few reads will cause the process to fail.

### Updating the pipeline

When you run the above command, Nextflow automatically pulls the pipeline code from GitHub and stores it as a cached version. When running the pipeline after this, it will always use the cached version if available - even if the pipeline has been updated since. To make sure that you're running the latest version of the pipeline, make sure that you regularly update the cached version of the pipeline:

```bash
nextflow pull genomic-medicine-sweden/metaval
```

### Reproducibility

It is a good idea to specify the pipeline version when running the pipeline on your data. This ensures that a specific version of the pipeline code and software are used when you run your pipeline. If you keep using the same tag, you'll be running the same version of the pipeline, even if there have been changes to the code since.

First, go to the [genomic-medicine-sweden/metaval releases page](https://github.com/genomic-medicine-sweden/metaval/releases) and find the latest pipeline version - numeric only (eg. `1.3.1`). Then specify this when running the pipeline with `-r` (one hyphen) - eg. `-r 1.3.1`. Of course, you can switch to another version by changing the number after the `-r` flag.

This version number will be logged in reports when you run the pipeline, so that you'll know what you used when you look back in the future. For example, at the bottom of the MultiQC reports.

To further assist in reproducibility, you can use share and reuse [parameter files](#running-the-pipeline) to repeat pipeline runs with the same settings without having to write out a command with every single parameter.

> [!TIP]
> If you wish to share such profile (such as upload as supplementary material for academic publications), make sure to NOT include cluster specific paths to files, nor institutional specific profiles.

## Core Nextflow arguments

> [!NOTE]
> These options are part of Nextflow and use a _single_ hyphen (pipeline parameters use a double-hyphen).

### `-profile`

Use this parameter to choose a configuration profile. Profiles can give configuration presets for different compute environments.

Several generic profiles are bundled with the pipeline which instruct the pipeline to use software packaged using different methods (Docker, Singularity, Podman, Shifter, Charliecloud, Apptainer, Conda) - see below.

> [!IMPORTANT]
> We highly recommend the use of Docker or Singularity containers for full pipeline reproducibility, however when this is not possible, Conda is also supported.

The pipeline also dynamically loads configurations from [https://github.com/nf-core/configs](https://github.com/nf-core/configs) when it runs, making multiple config profiles for various institutional clusters available at run time. For more information and to check if your system is supported, please see the [nf-core/configs documentation](https://github.com/nf-core/configs#documentation).

Note that multiple profiles can be loaded, for example: `-profile test,docker` - the order of arguments is important!
They are loaded in sequence, so later profiles can overwrite earlier profiles.

If `-profile` is not specified, the pipeline will run locally and expect all software to be installed and available on the `PATH`. This is _not_ recommended, since it can lead to different results on different machines dependent on the computer environment.

- `test`
  - A profile with a complete configuration for automated testing
  - Includes links to test data so needs no other parameters
- `docker`
  - A generic configuration profile to be used with [Docker](https://docker.com/)
- `singularity`
  - A generic configuration profile to be used with [Singularity](https://sylabs.io/docs/)
- `podman`
  - A generic configuration profile to be used with [Podman](https://podman.io/)
- `shifter`
  - A generic configuration profile to be used with [Shifter](https://nersc.gitlab.io/development/shifter/how-to-use/)
- `charliecloud`
  - A generic configuration profile to be used with [Charliecloud](https://hpc.github.io/charliecloud/)
- `apptainer`
  - A generic configuration profile to be used with [Apptainer](https://apptainer.org/)
- `wave`
  - A generic configuration profile to enable [Wave](https://seqera.io/wave/) containers. Use together with one of the above (requires Nextflow ` 24.03.0-edge` or later).
- `conda`
  - A generic configuration profile to be used with [Conda](https://conda.io/docs/). Please only use Conda as a last resort i.e. when it's not possible to run the pipeline with Docker, Singularity, Podman, Shifter, Charliecloud, or Apptainer.

### `-resume`

Specify this when restarting a pipeline. Nextflow will use cached results from any pipeline steps where the inputs are the same, continuing from where it got to previously. For input to be considered the same, not only the names must be identical but the files' contents as well. For more info about this parameter, see [this blog post](https://www.nextflow.io/blog/2019/demystifying-nextflow-resume.html).

You can also supply a run name to resume a specific run: `-resume [run-name]`. Use the `nextflow log` command to show previous run names.

### `-c`

Specify the path to a specific config file (this is a core Nextflow command). See the [nf-core website documentation](https://nf-co.re/usage/configuration) for more information.

## Custom configuration

### Resource requests

Whilst the default requirements set within the pipeline will hopefully work for most people and with most input data, you may find that you want to customise the compute resources that the pipeline requests. Each step in the pipeline has a default set of requirements for number of CPUs, memory and time. For most of the pipeline steps, if the job exits with any of the error codes specified [here](https://github.com/nf-core/rnaseq/blob/4c27ef5610c87db00c3c5a3eed10b1d161abf575/conf/base.config#L18) it will automatically be resubmitted with higher resources request (2 x original, then 3 x original). If it still fails after the third attempt then the pipeline execution is stopped.

To change the resource requests, please see the [max resources](https://nf-co.re/docs/usage/configuration#max-resources) and [tuning workflow resources](https://nf-co.re/docs/usage/configuration#tuning-workflow-resources) section of the nf-core website.

### Custom Containers

In some cases, you may wish to change the container or conda environment used by a pipeline steps for a particular tool. By default, nf-core pipelines use containers and software from the [biocontainers](https://biocontainers.pro/) or [bioconda](https://bioconda.github.io/) projects. However, in some cases the pipeline specified version maybe out of date.

To use a different container from the default container or conda environment specified in a pipeline, please see the [updating tool versions](https://nf-co.re/docs/usage/configuration#updating-tool-versions) section of the nf-core website.

### Custom Tool Arguments

A pipeline might not always support every possible argument or option of a particular tool used in pipeline. Fortunately, nf-core pipelines provide some freedom to users to insert additional parameters that the pipeline does not include by default.

To learn how to provide additional arguments to a particular tool of the pipeline, please see the [customising tool arguments](https://nf-co.re/docs/usage/configuration#customising-tool-arguments) section of the nf-core website.

### nf-core/configs

In most cases, you will only need to create a custom config as a one-off but if you and others within your organisation are likely to be running nf-core pipelines regularly and need to use the same settings regularly it may be a good idea to request that your custom config file is uploaded to the `nf-core/configs` git repository. Before you do this please can you test that the config file works with your pipeline of choice using the `-c` parameter. You can then create a pull request to the `nf-core/configs` repository with the addition of your config file, associated documentation file (see examples in [`nf-core/configs/docs`](https://github.com/nf-core/configs/tree/master/docs)), and amending [`nfcore_custom.config`](https://github.com/nf-core/configs/blob/master/nfcore_custom.config) to include your custom profile.

See the main [Nextflow documentation](https://www.nextflow.io/docs/latest/config.html) for more information about creating your own configuration files.

If you have any questions or issues please send us a message on [Slack](https://nf-co.re/join/slack) on the [`#configs` channel](https://nfcore.slack.com/channels/configs).

## Running in the background

Nextflow handles job submissions and supervises the running jobs. The Nextflow process must run until the pipeline is finished.

The Nextflow `-bg` flag launches Nextflow in the background, detached from your terminal so that the workflow does not stop if you log out of your session. The logs are saved to a file.

Alternatively, you can use `screen` / `tmux` or similar tool to create a detached session which you can log back into at a later time.
Some HPC setups also allow you to run nextflow within a cluster job submitted your job scheduler (from where it submits more jobs).

## Nextflow memory requirements

In some cases, the Nextflow Java virtual machines can start to request a large amount of memory.
We recommend adding the following line to your environment to limit this (typically in `~/.bashrc` or `~./bash_profile`):

```bash
NXF_OPTS='-Xms1g -Xmx4g'
```
