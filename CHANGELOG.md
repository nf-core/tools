# genomic-medicine-sweden/metaval: Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v1.0dev - [date]

Initial release of genomic-medicine-sweden/metaval, created with the [nf-core](https://nf-co.re/) template.

### `Added`

- Extract taxIDs of viruses
- Extract Kraken2 reads with KrakenTools
- Extract Centrifuge reads
- Extract DIAMOND reads
- Screen pathogens:
  - Map reads to the pathogen genome database using Bowtie2 for short reads and Minimap2 for long reads
  - Call consensus sequences for reads mapped to the pathogen genomes

### `Fixed`

### `Dependencies`

### `Deprecated`
