# nf-core/{{ cookiecutter.pipeline_slug }} installation

To start using the nf-core/{{ cookiecutter.pipeline_slug }} pipeline, follow the steps below:

1. [Install Nextflow](#1-install-nextflow)
2. [Install the pipeline](#2-install-the-pipeline)
    * [Automatic](#21-automatic)
    * [Offline](#22-offline)
    * [Development](#23-development)
3. [Pipeline configuration](#3-pipeline-configuration)
    * [Software deps: Docker and Singularity](#31-software-deps-docker-and-singularity)
    * [Software deps: Bioconda](#32-software-deps-bioconda)
    * [Configuration profiles](#33-configuration-profiles)
4. [Reference genomes](#4-reference-genomes)
5. [Appendices](#appendices)
    * [Running on UPPMAX](#running-on-uppmax)

## 1) Install NextFlow
Nextflow runs on most POSIX systems (Linux, Mac OSX etc). It can be installed by running the following commands:

```bash
# Make sure that Java v8+ is installed:
java -version

# Install Nextflow
curl -fsSL get.nextflow.io | bash

# Add Nextflow binary to your PATH:
mv nextflow ~/bin/
# OR system-wide installation:
# sudo mv nextflow /usr/local/bin
```

See [nextflow.io](https://www.nextflow.io/) for further instructions on how to install and configure Nextflow.

## 2) Install the pipeline

#### 2.1) Automatic
This pipeline itself needs no installation - NextFlow will automatically fetch it from GitHub if `nf-core/{{ cookiecutter.pipeline_name }}` is specified as the pipeline name.

#### 2.2) Offline
The above method requires an internet connection so that Nextflow can download the pipeline files. If you're running on a system that has no internet connection, you'll need to download and transfer the pipeline files manually:

```bash
wget https://github.com/nf-core/{{ cookiecutter.pipeline_name }}/archive/master.zip
unzip master.zip -d /my-pipelines/
cd /my_data/
nextflow run /my-pipelines/{{ cookiecutter.pipeline_slug }}-master
```

To stop nextflow from looking for updates online, you can tell it to run in offline mode by specifying the following environment variable in your ~/.bashrc file:

```bash
export NXF_OFFLINE='TRUE'
```

#### 2.3) Development

If you would like to make changes to the pipeline, it's best to make a fork on GitHub and then clone the files. Once cloned you can run the pipeline directly as above.


## 3) Pipeline configuration
By default, the pipeline runs with the `standard` configuration profile. This uses a number of sensible defaults for process requirements and is suitable for running on a simple (if powerful!) basic server. You can see this configuration in [`conf/base.config`](../conf/base.config).

Be warned of two important points about this default configuration:

1. The default profile uses the `local` executor
    * All jobs are run in the login session. If you're using a simple server, this may be fine. If you're using a compute cluster, this is bad as all jobs will run on the head node.
    * See the [nextflow docs](https://www.nextflow.io/docs/latest/executor.html) for information about running with other hardware backends. Most job scheduler systems are natively supported.
2. Nextflow will expect all software to be installed and available on the `PATH`

#### 3.1) Software deps: Docker and Singularity
Running the pipeline with the option `-profile singularity` or `-with-docker` tells Nextflow to enable either [Singularity](http://singularity.lbl.gov/) or Docker for this run. An image containing all of the software requirements will be automatically fetched and used (https://hub.docker.com/r/nf-core/{{ cookiecutter.pipeline_slug }}).

If running offline with Singularity, you'll need to download and transfer the Singularity image first:

```bash
singularity pull --name nfcore-{{ cookiecutter.pipeline_slug }}-[VERSION].simg shub://nfcore/{{ cookiecutter.pipeline_slug }}:[VERSION]
```

Once transferred, use `-profile singularity` but specify the path to the image file:

```bash
nextflow run /path/to/nf-core-{{ cookiecutter.pipeline_slug }} -profile singularity /path/to/{{ cookiecutter.pipeline_slug }}-[VERSION].simg
```

#### 3.2) Software deps: bioconda

If you're unable to use either Docker or Singularity but you have conda installed, you can use the bioconda environment that comes with the pipeline. Running this command will create a new conda environment with all of the required software installed:

```bash
conda env create -f environment.yml
conda clean -a # Recommended, not essential
source activate nfcore-{{ cookiecutter.pipeline_slug }}-1.3 # Name depends on version
```

The [`environment.yml`](../environment.yml) file is packaged with the pipeline. Note that you may need to download this file from the [GitHub project page](https://github.com/nf-core/{{ cookiecutter.pipeline_slug }}) if nextflow is automatically fetching the pipeline files. Ensure that the bioconda environment file version matches the pipeline version that you run.


#### 3.3) Configuration profiles

Nextflow can be configured to run on a wide range of different computational infrastructures. In addition to the above pipeline-specific parameters it is likely that you will need to define system-specific options. For more information, please see the [Nextflow documentation](https://www.nextflow.io/docs/latest/).

Whilst most parameters can be specified on the command line, it is usually sensible to create a configuration file for your environment.

If you are the only person to be running this pipeline, you can create your config file as `~/.nextflow/config` and it will be applied every time you run Nextflow. Alternatively, save the file anywhere and reference it when running the pipeline with `-c path/to/config`.

If you think that there are other people using the pipeline who would benefit from your configuration (eg. other common cluster setups), please let us know. We can add a new configuration and profile which can used by specifying `-profile <name>` when running the pipeline.

The pipeline comes with several such config profiles - see the installation appendices and usage documentation for more information.


## 4) Reference Genomes
The nf-core/{{ cookiecutter.pipeline_slug }} pipeline needs a reference genome for read alignment. Support for many common genomes is built in if running on UPPMAX or AWS, by using [AWS-iGenomes](https://ewels.github.io/AWS-iGenomes/).


## Appendices

#### Running on UPPMAX
To run the pipeline on the [Swedish UPPMAX](https://www.uppmax.uu.se/) clusters (`rackham`, `irma`, `bianca` etc), use the command line flag `-profile uppmax`. This tells Nextflow to submit jobs using the SLURM job executor with Singularity for software dependencies.

Note that you will need to specify your UPPMAX project ID when running a pipeline. To do this, use the command line flag `--project <project_ID>`. The pipeline will exit with an error message if you try to run it pipeline with the default UPPMAX config profile without a project.

**Optional Extra:** To avoid having to specify your project every time you run Nextflow, you can add it to your personal Nextflow config file instead. Add this line to `~/.nextflow/config`:

```nextflow
params.project = 'project_ID' // eg. b2017123
```