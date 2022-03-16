## Bumping a pipeline version number

When releasing a new version of a nf-core pipeline, version numbers have to be updated in several different places. The helper command `nf-core bump-version` automates this for you to avoid manual errors (and frustration!).

The command uses results from the linting process, so will only work with workflows that pass these tests.

Usage is `nf-core bump-version <new_version>`, eg:

```console
$ cd path/to/my_pipeline
$ nf-core bump-version 1.7
                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2



INFO     Changing version number from '1.6dev' to '1.7'
INFO     Updated version in 'nextflow.config'
           - version = '1.6dev'
           + version = '1.7'
           - process.container = 'nfcore/methylseq:dev'
           + process.container = 'nfcore/methylseq:1.7'


INFO     Updated version in '.github/workflows/ci.yml'
           - run: docker build --no-cache . -t nfcore/methylseq:dev
           + run: docker build --no-cache . -t nfcore/methylseq:1.7
           - docker tag nfcore/methylseq:dev nfcore/methylseq:dev
           + docker tag nfcore/methylseq:dev nfcore/methylseq:1.7


INFO     Updated version in 'environment.yml'
           - name: nf-core-methylseq-1.6dev
           + name: nf-core-methylseq-1.7


INFO     Updated version in 'Dockerfile'
           - ENV PATH /opt/conda/envs/nf-core-methylseq-1.6dev/bin:$PATH
           + ENV PATH /opt/conda/envs/nf-core-methylseq-1.7/bin:$PATH
           - RUN conda env export --name nf-core-methylseq-1.6dev > nf-core-methylseq-1.6dev.yml
           + RUN conda env export --name nf-core-methylseq-1.7 > nf-core-methylseq-1.7.yml
```

You can change the directory from the current working directory by specifying `--dir <pipeline_dir>`. To change the required version of Nextflow instead of the pipeline version number, use the flag `--nextflow`.
