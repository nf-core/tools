# genomic-medicine-sweden/metaval: Tutorials

This page provides a range of tutorials to give you additional guidance on setting up `genomic-medicine-sweden/metaval`. In this tutorial we will walk you through different workflows of the current pipeline. It assumes that you have the output files from the [nf-core/taxprofiler](https://github.com/nf-core/taxprofiler), generated using the following three classifiers: Kraken2, Centrifuge, and DIAMOND.

## Preparation

### Hardware

The datasets used should be small enough to run on your own laptop or a single server node.

If you wish to use a HPC cluster or cloud, and don't wish to use an 'interactive' session submitted to your scheduler, please see the [nf-core documentation](https://nf-co.re/docs/usage/configuration#introduction) on how to make a relevant config file.

You will need internet access and at least 1.5 GB of hardrive space.

### Software

The tutorial assumes you are on a Unix based operating system, and have already installed Nextflow as well a software environment system such as [Conda](https://docs.conda.io/en/latest/miniconda.html), [Docker](https://www.docker.com/), or [Singularity/Apptainer](https://apptainer.org/).
The tutorial will use Docker, however you can simply replace references to `docker` with `conda`, `singularity`, or `apptainer` accordingly.

### Data

**genomic-medicine-sweden/metaval** is a bioinformatics pipeline for post-processing the results of [nf-core/taxprofiler](https://github.com/nf-core/taxprofiler). In this tutorial, we will use the output files from `nf-core/taxprofilers` for a subset of metagenomic sequencing data, including one Illumina sample and one Nanopore sample. The taxonomy path should be specified when running nf-core/taxprofiler, as this information from the `taxpasta` output will be used by `genomic-medicine-sweden/metaval`. Below is an example or running `nf-core/taxprofiler`. Please check the [usage of nf-core/taxprofiler](https://github.com/nf-core/taxprofiler/tree/master/docs) for detailed instructions on how to run it.

#### Run nf-core/taxprofiler

```bash
nextflow run nf-core/taxprofiler -profile hasta,singularity \
--input samplesheet.csv --databases databases.csv --outdir taxprofiler_results \
--perform_shortread_qc --perform_longread_qc --perform_shortread_hostremoval \
--perform_longread_hostremoval --hostremoval_reference GCF_009914755.1_T2T-CHM13v2.0_genomic.fna \
--save_hostremoval_index --save_hostremoval_unmapped \
--run_kraken2 --kraken2_save_reads --kraken2_save_readclassifications \
--run_centrifuge --centrifuge_save_reads --run_diamond \
--run_profile_standardisation --taxpasta_taxonomy_dir taxonomy --taxpasta_add_lineage

```

#### Download data

First we will create a directory to run the whole tutorial in.

```bash
mkdir metaval-tutorial
cd metaval-tutorial/

```

Reads could be raw FASTQ files, filtered FASTQ files, or FASTQ files with host genomes removed. In this example, FASTQ files with host genomes removed were used.

```bash
# reads:
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439790_SRR13439790.unmapped_1.fastq.gz
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439790_SRR13439790.unmapped_2.fastq.gz
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439799_SRR13439799.unmapped_other.fastq.gz
# reference
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/333a4af341ac9cba6106e6ebd295fc64e28d58bd/reference/reference.fasta
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/333a4af341ac9cba6106e6ebd295fc64e28d58bd/reference/accession2taxid.map
# kraken2
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439790_pe_SRR13439790_k2_pluspf.kraken2.kraken2.report.txt
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439790_pe_SRR13439790_k2_pluspf.kraken2.kraken2.classifiedreads.txt
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439799_se_SRR13439799_k2_pluspf.kraken2.kraken2.report.txt
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439799_se_SRR13439799_k2_pluspf.kraken2.kraken2.classifiedreads.txt
# centrifuge
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439790_pe_SRR13439790_p_compressed+h+v.centrifuge.txt
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439790_pe_SRR13439790_p_compressed+h+v.centrifuge.results.txt
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439799_se_SRR13439799_p_compressed+h+v.centrifuge.txt
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439799_se_SRR13439799_p_compressed+h+v.centrifuge.results.txt
# diamond
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439790_pe_SRR13439790_diamond.diamond.tsv
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/SRR13439799_se_SRR13439799_diamond.diamond.tsv
# taxpasta
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/kraken2_k2_pluspf.tsv
curl -O https://raw.githubusercontent.com/genomic-medicine-sweden/test-datasets/metaval/testdata/centrifuge_p_compressed+h+v.tsv

```

### Preparing input samplesheet

You provide the output files of `nf-core/taxprofiler` via a input 'samplesheet' `.csv` file.
This is a 13-column table if you would like to run the current pipeline for three classifiers `Kraken2`,`Centrifuge` and `DIAMOND`.

Open a text editor, and create a file called `samplesheet.csv`.
Copy and paste the following lines into the file and save it.

```csv title="samplesheet.csv"
sample,run_accession,instrument_platform,fastq_1,fastq_2,kraken2_report,kraken2_result,kraken2_taxpasta,centrifuge_report,centrifuge_result,centrifuge_taxpasta,diamond,diamond_taxpasta
SRR13439790,SRR13439790,ILLUMINA,SRR13439790_SRR13439790.unmapped_1.fastq.gz,SRR13439790_SRR13439790.unmapped_2.fastq.gz,SRR13439790_pe_SRR13439790_k2_pluspf.kraken2.kraken2.report.txt,SRR13439790_pe_SRR13439790_k2_pluspf.kraken2.kraken2.classifiedreads.txt,kraken2_k2_pluspf.tsv,SRR13439790_pe_SRR13439790_p_compressed+h+v.centrifuge.txt,SRR13439790_pe_SRR13439790_p_compressed+h+v.centrifuge.results.txt,centrifuge_p_compressed+h+v.tsv,SRR13439790_pe_SRR13439790_diamond.diamond.tsv,diamond_diamond.tsv
SRR13439799,SRR13439799,OXFORD_NANOPORE,SRR13439799_SRR13439799.unmapped_other.fastq.gz,,SRR13439799_se_SRR13439799_k2_pluspf.kraken2.kraken2.report.txt,SRR13439799_se_SRR13439799_k2_pluspf.kraken2.kraken2.classifiedreads.txt,kraken2_k2_pluspf.tsv,SRR13439799_se_SRR13439799_p_compressed+h+v.centrifuge.txt,SRR13439799_se_SRR13439799_p_compressed+h+v.centrifuge.results.txt,centrifuge_p_compressed+h+v.tsv,SRR13439799_se_SRR13439799_diamond.diamond.tsv,diamond_diamond.tsv

```

If you had placed your nf-core/taxprofiler output files elsewhere, you would give the full path (i.e., with relevant directories) to the `fastq_1`, `fastq_2` and `fasta` columns.

### Running the pipeline

**genomic-medicine-sweden/metaval** can perform three different workflows:

- pathogen screening
- verify identified viruses
- verify user-defined taxIDs.
  In this tutorial we will go through each workflow with example command lines.

#### Pathogen screening

This workflow is activated by enabling the `--perform_screen_pathogens` option. A reference database of pathogen genomes, the corresponding accessions and taxid map file should be prepared.

```bash
git clone https://github.com/genomic-medicine-sweden/metaval.git
nextflow run metaval/main.nf -profile singularity --input samplesheet.csv --outdir pathogen_screen_result \
--pathogens_genomes reference.fasta --accession2taxid accession2taxid.map \
--perform_screen_pathogens --perform_longread_consensus --perform_shortread_consensus \
--longread_consensus_tool --min_read_counts 20

```

#### Verify identified viruses

This workflow is activated by enabling the `--perform_extract_reads` option and disabling the `--taxid`.

```bash
git clone https://github.com/genomic-medicine-sweden/metaval.git
nextflow run metaval/main.nf -profile singularity --input samplesheet.csv --outdir identified_viruses_results \
--perform_extract_reads --extract_kraken2_reads --extract_centrifuge_reads --extract_diamond_reads \
--perform_shortread_denovo --perform_longread_denovo --min_read_counts 20

```

#### Verify user-defined taxIDs

This workflow is activated by enabling the ´--perform_extract_reads´ option and the `--taxid` option, allowing users to define a list of taxIDs. It is not limited to viral taxIDs and can include bacteria, fungi, archaea, parasites, or plasmids.

```bash
git clone https://github.com/genomic-medicine-sweden/metaval.git
nextflow run metaval/main.nf -profile singularity --input samplesheet.csv --outdir identified_viruses_results \
--perform_extract_reads --taxid "211044 2886042 1920753 2491323 1826872 878220" \
--extract_kraken2_reads --extract_centrifuge_reads --extract_diamond_reads \
--perform_shortread_denovo --perform_longread_denovo --min_read_counts 20

```
