---
title: Download
description: Downloading pipelines for offline use
weight: 50
section: pipelines
---

Sometimes you may need to run an nf-core pipeline on a server or HPC system that has no internet connection.
In this case you will need to fetch the pipeline files first, then manually transfer them to your system.

To make this process easier and ensure accurate retrieval of correctly versioned code and software containers, we have written a download helper tool.

The `nf-core download` command will download both the pipeline code and the [institutional nf-core/configs](https://github.com/nf-core/configs) files. It can also optionally download any singularity image files that are required.

If run without any arguments, the download tool will interactively prompt you for the required information.
Each option has a flag, if all are supplied then it will run without any user input needed.

<!-- RICH-CODEX
working_dir: tmp
-->

![`nf-core download rnaseq -r 3.8 --outdir nf-core-rnaseq -x none -s none -d`](../images/nf-core-download.svg)

Once downloaded, you will see something like the following file structure for the downloaded pipeline:

<!-- RICH-CODEX
working_dir: tmp
-->

![`tree -L 2 nf-core-rnaseq/`](../images/nf-core-download-tree.svg)

You can run the pipeline by simply providing the directory path for the `workflow` folder to your `nextflow run` command:

```bash
nextflow run /path/to/download/nf-core-rnaseq-dev/workflow/ --input mydata.csv --outdir results  # usual parameters here
```

:::note
If you downloaded Singularity container images, you will need to use `-profile singularity` or have it enabled in your config file.
:::

### Downloaded nf-core configs

The pipeline files are automatically updated (`params.custom_config_base` is set to `../configs`), so that the local copy of institutional configs are available when running the pipeline.
So using `-profile <NAME>` should work if available within [nf-core/configs](https://github.com/nf-core/configs).

:::warning
This option is not available when downloading a pipeline for use with [Nextflow Tower](#adapting-downloads-to-nextflow-tower) because the application manages all configurations separately.
:::

### Downloading Apptainer containers

If you're using [Singularity](https://apptainer.org) (Apptainer), the `nf-core download` command can also fetch the required container images for you.
To do this, select `singularity` in the prompt or specify `--container-system singularity` in the command.
Your archive / target output directory will then also include a separate folder `singularity-containers`.

The downloaded workflow files are again edited to add the following line to the end of the pipeline's `nextflow.config` file:

```nextflow
singularity.cacheDir = "${projectDir}/../singularity-images/"
```

This tells Nextflow to use the `singularity-containers` directory relative to the workflow for the singularity image cache directory.
All images should be downloaded there, so Nextflow will use them instead of trying to pull from the internet.

#### Singularity cache directory

We highly recommend setting the `$NXF_SINGULARITY_CACHEDIR` environment variable on your system, even if that is a different system to where you will be running Nextflow.

If found, the tool will fetch the Singularity images to this directory first before copying to the target output archive / directory.
Any images previously fetched will be found there and copied directly - this includes images that may be shared with other pipelines or previous pipeline version downloads or download attempts.

If you are running the download on the same system where you will be running the pipeline (eg. a shared filesystem where Nextflow won't have an internet connection at a later date), you can choose to _only_ use the cache via a prompt or cli options `--container-cache-utilisation amend`. This instructs `nf-core download` to fetch all Singularity images to the `$NXF_SINGULARITY_CACHEDIR` directory but does _not_ copy them to the workflow archive / directory. The workflow config file is _not_ edited. This means that when you later run the workflow, Nextflow will just use the cache folder directly.

If you are downloading a workflow for a different system, you can provide information about the contents of its image cache to `nf-core download`. To avoid unnecessary container image downloads, choose `--container-cache-utilisation remote` and provide a list of already available images as plain text file to `--container-cache-index my_list_of_remotely_available_images.txt`. To generate this list on the remote system, run `find $NXF_SINGULARITY_CACHEDIR -name "*.img" > my_list_of_remotely_available_images.txt`. The tool will then only download and copy images into your output directory, which are missing on the remote system.

#### How the Singularity image downloads work

The Singularity image download finds containers using two methods:

1. It runs `nextflow config` on the downloaded workflow to look for a `process.container` statement for the whole pipeline.
   This is the typical method used for DSL1 pipelines.
2. It scrapes any files it finds with a `.nf` file extension in the workflow `modules` directory for lines
   that look like `container = "xxx"`. This is the typical method for DSL2 pipelines, which have one container per process.

Some DSL2 modules have container addresses for docker (eg. `biocontainers/fastqc:0.11.9--0`) and also URLs for direct downloads of a Singularity container (eg. `https://depot.galaxyproject.org/singularity/fastqc:0.11.9--0`).
Where both are found, the download URL is preferred.

Once a full list of containers is found, they are processed in the following order:

1. If the target image already exists, nothing is done (eg. with `$NXF_SINGULARITY_CACHEDIR` and `--container-cache-utilisation amend` specified)
2. If found in `$NXF_SINGULARITY_CACHEDIR` and `--container-cache-utilisation copy` is specified, they are copied to the output directory
3. If they start with `http` they are downloaded directly within Python (default 4 at a time, you can customise this with `--parallel-downloads`)
4. If they look like a Docker image name, they are fetched using a `singularity pull` command. Choose the container libraries (registries) queried by providing one or multiple `--container-library` parameter(s). For example, if you call `nf-core download` with `-l quay.io -l ghcr.io -l docker.io`, every image will be pulled from `quay.io` unless an error is encountered. Subsequently, `ghcr.io` and then `docker.io` will be queried for any image that has failed before.
   - This requires Singularity/Apptainer to be installed on the system and is substantially slower

Note that compressing many GBs of binary files can be slow, so specifying `--compress none` is recommended when downloading Singularity images that are copied to the output directory.

If the download speeds are much slower than your internet connection is capable of, you can set `--parallel-downloads` to a large number to download loads of images at once.

### Adapting downloads to Nextflow Tower

[seqeralabs® Nextflow Tower](https://cloud.tower.nf/) provides a graphical user interface to oversee pipeline runs, gather statistics and configure compute resources. While pipelines added to _Tower_ are preferably hosted at a Git service, providing them as disconnected, self-reliant repositories is also possible for premises with restricted network access. Choosing the `--tower` flag will download the pipeline in an appropriate form.

Subsequently, the `*.git` folder can be moved to it's final destination and linked with a pipeline in _Tower_ using the `file:/` prefix.

:::tip
Also without access to Tower, pipelines downloaded with the `--tower` flag can be run: `nextflow run -r 2.5 file:/path/to/pipelinedownload.git`. Downloads in this format allow you to include multiple revisions of a pipeline in a single file, but require that the revision (e.g. `-r 2.5`) is always explicitly specified.
:::
