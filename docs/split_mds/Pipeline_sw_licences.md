## Pipeline software licences

Sometimes it's useful to see the software licences of the tools used in a pipeline.
You can use the `licences` subcommand to fetch and print the software licence from each conda / PyPI package used in an nf-core pipeline.

> NB: Currently this command does not work for DSL2 pipelines. This will be addressed [soon](https://github.com/nf-core/tools/issues/1155).

```console
$ nf-core licences rnaseq

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

  INFO     Fetching licence information for 25 tools
  INFO     Warning: This tool only prints licence information for the software tools packaged using conda.
  INFO     The pipeline may use other software and dependencies not described here.
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Package Name                      ┃ Version ┃ Licence              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ stringtie                         │ 2.0     │ Artistic License 2.0 │
│ bioconductor-summarizedexperiment │ 1.14.0  │ Artistic-2.0         │
│ preseq                            │ 2.0.3   │ GPL                  │
│ trim-galore                       │ 0.6.4   │ GPL                  │
│ bioconductor-edger                │ 3.26.5  │ GPL >=2              │
│ fastqc                            │ 0.11.8  │ GPL >=3              │
│ bioconductor-tximeta              │ 1.2.2   │ GPLv2                │
│ qualimap                          │ 2.2.2c  │ GPLv2                │
│ r-gplots                          │ 3.0.1.1 │ GPLv2                │
│ r-markdown                        │ 1.1     │ GPLv2                │
│ rseqc                             │ 3.0.1   │ GPLv2                │
│ bioconductor-dupradar             │ 1.14.0  │ GPLv3                │
│ deeptools                         │ 3.3.1   │ GPLv3                │
│ hisat2                            │ 2.1.0   │ GPLv3                │
│ multiqc                           │ 1.7     │ GPLv3                │
│ salmon                            │ 0.14.2  │ GPLv3                │
│ star                              │ 2.6.1d  │ GPLv3                │
│ subread                           │ 1.6.4   │ GPLv3                │
│ r-base                            │ 3.6.1   │ GPLv3.0              │
│ sortmerna                         │ 2.1b    │ LGPL                 │
│ gffread                           │ 0.11.4  │ MIT                  │
│ picard                            │ 2.21.1  │ MIT                  │
│ samtools                          │ 1.9     │ MIT                  │
│ r-data.table                      │ 1.12.4  │ MPL-2.0              │
│ matplotlib                        │ 3.0.3   │ PSF-based            │
└───────────────────────────────────┴─────────┴──────────────────────┘
```
