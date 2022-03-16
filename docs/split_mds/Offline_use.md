## Downloading pipelines for offline use

Sometimes you may need to run an nf-core pipeline on a server or HPC system that has no internet connection.
In this case you will need to fetch the pipeline files first, then manually transfer them to your system.

To make this process easier and ensure accurate retrieval of correctly versioned code and software containers, we have written a download helper tool.

The `nf-core download` command will download both the pipeline code and the [institutional nf-core/configs](https://github.com/nf-core/configs) files. It can also optionally download any singularity image files that are required.

If run without any arguments, the download tool will interactively prompt you for the required information.
Each option has a flag, if all are supplied then it will run without any user input needed.

```console
$ nf-core download

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2


Specify the name of a nf-core pipeline or a GitHub repository name (user/repo).
? Pipeline name: rnaseq
? Select release / branch: 3.0  [release]

In addition to the pipeline code, this tool can download software containers.
? Download software container images: singularity

Nextflow and nf-core can use an environment variable called $NXF_SINGULARITY_CACHEDIR that is a path to a directory where remote Singularity
images are stored. This allows downloaded images to be cached in a central location.
? Define $NXF_SINGULARITY_CACHEDIR for a shared Singularity image download folder? [y/n]: y
? Specify the path: cachedir/

So that $NXF_SINGULARITY_CACHEDIR is always defined, you can add it to your ~/.bashrc file. This will then be autmoatically set every time you open a new terminal. We can add the following line to this file for you:
export NXF_SINGULARITY_CACHEDIR="/path/to/demo/cachedir"
? Add to ~/.bashrc ? [y/n]: n

If transferring the downloaded files to another system, it can be convenient to have everything compressed in a single file.
This is not recommended when downloading Singularity images, as it can take a long time and saves very little space.
? Choose compression type: none
INFO     Saving 'nf-core/rnaseq
          Pipeline release: '3.0'
          Pull containers: 'singularity'
          Using $NXF_SINGULARITY_CACHEDIR': /path/to/demo/cachedir
          Output directory: 'nf-core-rnaseq-3.0'
INFO     Downloading workflow files from GitHub
INFO     Downloading centralised configs from GitHub
INFO     Found 29 containers
Downloading singularity images ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% • 29/29 completed
```

Once downloaded, you will see something like the following file structure for the downloaded pipeline:

```console
$ tree -L 2 nf-core-rnaseq-3.0/

nf-core-rnaseq-3.0
├── configs
│   ├── ..truncated..
│   ├── nextflow.config
│   ├── nfcore_custom.config
│   └── pipeline
├── singularity-images
│   ├── containers.biocontainers.pro-s3-SingImgsRepo-biocontainers-v1.2.0_cv1-biocontainers_v1.2.0_cv1.img.img
│   ├── ..truncated..
│   └── depot.galaxyproject.org-singularity-umi_tools-1.1.1--py38h0213d0e_1.img
└── workflow
    ├── CHANGELOG.md
    ├── ..truncated..
    └── main.nf
```

You can run the pipeline by simply providing the directory path for the `workflow` folder to your `nextflow run` command:

```bash
nextflow run /path/to/download/nf-core-rnaseq-3.0/workflow/ --input mydata.csv   # usual parameters here
```

### Downloaded nf-core configs

The pipeline files are automatically updated (`params.custom_config_base` is set to `../configs`), so that the local copy of institutional configs are available when running the pipeline.
So using `-profile <NAME>` should work if available within [nf-core/configs](https://github.com/nf-core/configs).