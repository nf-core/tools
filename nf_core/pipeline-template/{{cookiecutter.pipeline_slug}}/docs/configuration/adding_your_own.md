# {{ cookiecutter.pipeline_name }}: Configuration for other clusters

It is entirely possible to run this pipeline on other clusters, though you will need to set up your own config file so that the pipeline knows how to work with your cluster.

> If you think that there are other people using the pipeline who would benefit from your configuration (eg. other common cluster setups), please let us know. We can add a new configuration and profile which can used by specifying `-profile <name>` when running the pipeline.

If you are the only person to be running this pipeline, you can create your config file as `~/.nextflow/config` and it will be applied every time you run Nextflow. Alternatively, save the file anywhere and reference it when running the pipeline with `-c path/to/config` (see the [Nextflow documentation](https://www.nextflow.io/docs/latest/config.html) for more).

A basic configuration comes with the pipeline, which runs by default (the `standard` config profile - see [`conf/base.config`](../conf/base.config)). This means that you only need to configure the specifics for your system and overwrite any defaults that you want to change.

## Cluster Environment
By default, pipeline uses the `local` Nextflow executor - in other words, all jobs are run in the login session. If you're using a simple server, this may be fine. If you're using a compute cluster, this is bad as all jobs will run on the head node.

To specify your cluster environment, add the following line to your config file:

```nextflow
process {
  executor = 'YOUR_SYSTEM_TYPE'
}
```

Many different cluster types are supported by Nextflow. For more information, please see the [Nextflow documentation](https://www.nextflow.io/docs/latest/executor.html).

Note that you may need to specify cluster options, such as a project or queue. To do so, use the `clusterOptions` config option:

```nextflow
process {
  executor = 'SLURM'
  clusterOptions = '-A myproject'
}
```


## Software Requirements
To run the pipeline, several software packages are required. How you satisfy these requirements is essentially up to you and depends on your system. If possible, we _highly_ recommend using either Docker or Singularity.

### Docker
Docker is a great way to run {{ cookiecutter.pipeline_name }}, as it manages all software installations and allows the pipeline to be run in an identical software environment across a range of systems.

Nextflow has [excellent integration](https://www.nextflow.io/docs/latest/docker.html) with Docker, and beyond installing the two tools, not much else is required.

First, install docker on your system: [Docker Installation Instructions](https://docs.docker.com/engine/installation/)

Then, simply run the analysis pipeline:
```bash
nextflow run {{ cookiecutter.github_repo }} -profile docker --reads '<path to your reads>'
```

Nextflow will recognise `{{ cookiecutter.github_repo }}` and download the pipeline from GitHub. The `-profile docker` configuration lists the [{{ cookiecutter.dockerhub_slug }}](https://hub.docker.com/r/{{ cookiecutter.dockerhub_slug }}/) image that we have created and is hosted at dockerhub, and this is downloaded.

The public docker images are tagged with the same version numbers as the code, which you can use to ensure reproducibility. When running the pipeline, specify the pipeline version with `-r`, for example `-r v1.3`. This uses pipeline code and docker image from this tagged version.

To add docker support to your own config file (instead of using the `docker` profile, which runs locally), add the following:

```nextflow
docker {
  enabled = true
}
process {
  container = wf_container
}
```

The variable `wf_container` is defined dynamically and automatically specifies the image tag if Nextflow is running with `-r`.

A test suite for docker comes with the pipeline, and can be run by moving to the [`tests` directory](https://github.com/{{ cookiecutter.github_repo }}/tree/master/tests) and running `./run_test.sh`. This will download a small yeast genome and some data, and attempt to run the pipeline through docker on that small dataset. This is automatically run using [Travis](https://travis-ci.org/{{ cookiecutter.github_repo }}/) whenever changes are made to the pipeline.

### Singularity image
Many HPC environments are not able to run Docker due to security issues. [Singularity](http://singularity.lbl.gov/) is a tool designed to run on such HPC systems which is very similar to Docker. Even better, it can use create images directly from dockerhub.

To use the singularity image for a single run, use `-with-singularity 'docker://{{ cookiecutter.github_repo }}'`. This will download the docker container from dockerhub and create a singularity image for you dynamically.

To specify singularity usage in your pipeline config file, add the following:

```nextflow
singularity {
  enabled = true
}
process {
  container = "docker://$wf_container"
}
```

The variable `wf_container` is defined dynamically and automatically specifies the image tag if Nextflow is running with `-r`.

If you intend to run the pipeline offline, nextflow will not be able to automatically download the singularity image for you. Instead, you'll have to do this yourself manually first, transfer the image file and then point to that.

First, pull the image file where you have an internet connection:

```bash
singularity pull --name {{ cookiecutter.pipeline_slug }}.img docker://{{ cookiecutter.github_repo }}
```

Then transfer this file and run the pipeline with this path:

```bash
nextflow run /path/to/{{ cookiecutter.pipeline_slug }} -with-singularity /path/to/{{ cookiecutter.pipeline_slug }}.img
```


### Manual Installation
As a last resort, you may need to install the required software manually. We recommend using [Bioconda](https://bioconda.github.io/) to do this. The following instructions are an example only and will not be updated with the pipeline.

#### 1) Install miniconda in your home directory
``` bash
cd
wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

#### 2) Add the bioconda conda channel (and others)
```bash
conda config --add channels anaconda
conda config --add channels conda-forge
conda config --add channels defaults
conda config --add channels r
conda config --add channels bioconda
conda config --add channels salilab
```

#### 3) Create a conda environment, with all necessary packages:
```bash
conda create --name {{ cookiecutter.pipeline_slug }}_py2.7 python=2.7
source activate {{ cookiecutter.pipeline_slug }}_py2.7
conda install --yes \
    fastqc \
    multiqc
```
_(Feel free to adjust versions as required.)_

##### 4) Usage
Once created, the conda environment can be activated before running the pipeline and deactivated afterwards:

```bash
source activate {{ cookiecutter.pipeline_slug }}_py2.7
# run pipeline
source deactivate
```