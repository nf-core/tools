# {{ cookiecutter.pipeline_name }}: Reference Genomes Configuration

The {{ cookiecutter.pipeline_name }} pipeline needs a reference genome for alignment and annotation. If not already available, start by downloading the relevant reference, for example from [illumina iGenomes](https://support.illumina.com/sequencing/sequencing_software/igenome.html).

The minimal requirements are a FASTA file.

## Adding paths to a config file
Specifying long paths every time you run the pipeline is a pain. To make this easier, the pipeline comes configured to understand reference genome keywords which correspond to preconfigured paths, meaning that you can just specify `--genome ID` when running the pipeline. 

Note that this genome key can also be specified in a config file if you always use the same genome.

To use this system, add paths to your config file using the following template:

```nextflow
params {
  genomes {
    'YOUR-ID' {
      fasta  = '<PATH TO FASTA FILE>/genome.fa'
    }
    'OTHER-GENOME' {
      // [..]
    }
  }
  // Optional - default genome. Ignored if --genome 'OTHER-GENOME' specified on command line
  genome = 'YOUR-ID'
}
```

You can add as many genomes as you like as long as they have unique IDs.

## illumina iGenomes
To make the use of reference genomes easier, illumina has developed a centralised resource called [iGenomes](https://support.illumina.com/sequencing/sequencing_software/igenome.html). Multiple reference index types are held together with consistent structure for multiple genomes.

If possible, we recommend making this resource available on your cluster. We have put a copy of iGenomes up onto AWS S3 hosting and this pipeline is configured to use this for some profiles (`docker`, `aws`). These profiles will automatically pull the required reference files when you run the pipeline.

To add iGenomes to your config file, add the following line to the end of your config file:

```nextflow
includeConfig '/path/to/{{ cookiecutter.pipeline_name }}/conf/igenomes.config'
```

This works best when you have a `profile` set up in the pipeline - see [`nextflow.config`](../../nextflow.config).

The hosting fees for AWS iGenomes are currently funded by a grant from Amazon. We hope that this work will be extended past the end of the grant expiry date (mid 2018), but we can't be sure at this point.

For more information about the AWS iGenomes, see https://ewels.github.io/AWS-iGenomes/
