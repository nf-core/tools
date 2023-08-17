---
title: Installation & Update
description: Installation and update instructions for nf-core/tools
weight: 10
section: general
---

## Bioconda

You can install `nf-core/tools` from [bioconda](https://bioconda.github.io/recipes/nf-core/README.html).

First, install conda and configure the channels to use bioconda
(see the [bioconda documentation](https://bioconda.github.io/index.html#usage)).
Then, just run the conda installation command:

```bash
conda install nf-core
```

Alternatively, you can create a new environment with both nf-core/tools and nextflow:

```bash
conda create --name nf-core python=3.8 nf-core nextflow
conda activate nf-core
```

## Python Package Index

`nf-core/tools` can also be installed from [PyPI](https://pypi.python.org/pypi/nf-core/) using pip as follows:

```bash
pip install nf-core
```

## Docker image

There is a docker image that you can use to run `nf-core/tools` that has all of the requirements packaged (including Nextflow) and so should work out of the box. It is called [`nfcore/tools`](https://hub.docker.com/r/nfcore/tools) _**(NB: no hyphen!)**_

You can use this container on the command line as follows:

```bash
docker run -itv `pwd`:`pwd` -w `pwd` -u $(id -u):$(id -g) nfcore/tools
```

- `-i` and `-t` are needed for the interactive cli prompts to work (this tells Docker to use a pseudo-tty with stdin attached)
- The `-v` argument tells Docker to bind your current working directory (`pwd`) to the same path inside the container, so that files created there will be saved to your local file system outside of the container.
- `-w` sets the working directory in the container to this path, so that it's the same as your working directory outside of the container.
- `-u` sets your local user account as the user inside the container, so that any files created have the correct ownership permissions

After the above base command, you can use the regular command line flags that you would use with other types of installation.
For example, to launch the `viralrecon` pipeline:

```bash
docker run -itv `pwd`:`pwd` -w `pwd` -u $(id -u):$(id -g) nfcore/tools launch viralrecon -r 1.1.0
```

If you use `$NXF_SINGULARITY_CACHEDIR` for downloads, you'll also need to make this folder and environment variable available to the continer:

```bash
docker run -itv `pwd`:`pwd` -w `pwd` -u $(id -u):$(id -g) -v $NXF_SINGULARITY_CACHEDIR:$NXF_SINGULARITY_CACHEDIR -e NXF_SINGULARITY_CACHEDIR nfcore/tools launch viralrecon -r 1.1.0
```

### Docker bash alias

The above base command is a bit of a mouthful to type, to say the least.
To make it easier to use, we highly recommend adding the following bash alias to your `~/.bashrc` file:

```bash
alias nf-core="docker run -itv `pwd`:`pwd` -w `pwd` -u $(id -u):$(id -g) nfcore/tools"
```

Once applied (you may need to reload your shell) you can just use the `nf-core` command instead:

```bash
nf-core list
```

### Docker versions

You can use docker image tags to specify the version you would like to use. For example, `nfcore/tools:dev` for the latest development version of the code, or `nfcore/tools:1.14` for version `1.14` of tools.
If you omit this, it will default to `:latest`, which should be the latest stable release.

If you need a specific version of Nextflow inside the container, you can build an image yourself.
Clone the repo locally and check out whatever version of nf-core/tools that you need.
Then build using the `--build-arg NXF_VER` flag as follows:

```bash
docker build -t nfcore/tools:dev . --build-arg NXF_VER=20.04.0
```

## Development version

If you would like the latest development version of tools, the command is:

```bash
pip install --upgrade --force-reinstall git+https://github.com/nf-core/tools.git@dev
```

If you intend to make edits to the code, first make a fork of the repository and then clone it locally.
Go to the cloned directory and install with pip (also installs development requirements):

```bash
pip install --upgrade -r requirements-dev.txt -e .
```

## Using a specific Python interpreter

If you prefer, you can also run tools with a specific Python interpreter.
The command line usage and flags are then exactly the same as if you ran with the `nf-core` command.
Note that the module is `nf_core` with an underscore, not a hyphen like the console command.

For example:

```bash
python -m nf_core --help
python3 -m nf_core list
~/my_env/bin/python -m nf_core create --name mypipeline --description "This is a new skeleton pipeline"
```

## Using with your own Python scripts

The tools functionality is written in such a way that you can import it into your own scripts.
For example, if you would like to get a list of all available nf-core pipelines:

```python
import nf_core.list
wfs = nf_core.list.Workflows()
wfs.get_remote_workflows()
for wf in wfs.remote_workflows:
    print(wf.full_name)
```

Please see [https://nf-co.re/tools-docs/](https://nf-co.re/tools-docs/) for the function documentation.

## Automatic version check

nf-core/tools automatically checks the web to see if there is a new version of nf-core/tools available.
If you would prefer to skip this check, set the environment variable `NFCORE_NO_VERSION_CHECK`. For example:

```bash
export NFCORE_NO_VERSION_CHECK=1
```

## Update tools

It is advisable to keep nf-core/tools updated to the most recent version. The command to update depends on the system used to install it, for example if you have installed it with conda you can use:

```bash
conda update nf-core
```

if you used pip:

```bash
pip install --upgrade nf-core
```

Please refer to the respective documentation for further details to manage packages, as for example [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-pkgs.html#updating-packages) or [pip](https://packaging.python.org/en/latest/tutorials/installing-packages/#upgrading-packages).

## Activate shell completions for nf-core/tools

Auto-completion for the `nf-core` command is available for bash, zsh and fish. To activate it, add the following lines to the respective shell config files.

| shell | shell config file                         | command                                            |
| ----- | ----------------------------------------- | -------------------------------------------------- |
| bash  | `~/.bashrc`                               | `eval "$(_NF_CORE_COMPLETE=bash_source nf-core)"`  |
| zsh   | `~/.zshrc`                                | `eval "$(_NF_CORE_COMPLETE=zsh_source nf-core)"`   |
| fish  | `~/.config/fish/completions/nf-core.fish` | `eval (env _NF_CORE_COMPLETE=fish_source nf-core)` |

After a restart of the shell session you should have auto-completion for the `nf-core` command and all its sub-commands and options.

:::note
The added line will run the command `nf-core` (which will also slow down startup time of your shell). You should therefore either have the nf-core/tools installed globally.
You can also wrap it inside `if type nf-core > /dev/null; then ` \<YOUR EVAL CODE LINE\> `fi` for bash and zsh or `if command -v nf-core &> /dev/null eval (env _NF_CORE_COMPLETE=fish_source nf-core) end` for fish. You need to then source the config in your environment for the completions to be activated.
:::

:::info
If you see the error `command not found compdef` , be sure that your config file contains the line `autoload -Uz compinit && compinit` before the eval line.
:::
