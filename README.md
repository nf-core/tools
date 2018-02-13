<img src="https://nf-core.github.io/assets/logo/nf-core-logo.png" width="400">

# [nf-core/tools](https://github.com/nf-core/tools)
A python package with helper tools for the nf-core community.

## Installation
Install the package with the following command:

```
pip install --upgrade --force-reinstall git+https://github.com/nf-core/tools.git
```

Alternatively, if you would like to edit the files locally:

```bash
# You should probably specify your fork instead
git clone https://github.com/nf-core/tools.git nf-core-tools
cd nf-core-tools
python setup.py develop
```

## Linting
Run the `lint` subcommand on a pipeline directory to check that it conforms to the nf-core community guidelines. This is the same test that is used on all automated tests. For example:

```
nf-core lint path/to/my_pipeline
```
