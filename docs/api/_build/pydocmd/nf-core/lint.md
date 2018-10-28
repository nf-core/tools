<h1 id="nf_core.lint">nf_core.lint</h1>

Linting policy for nf-core pipeline projects.

Tests Nextflow-based pipelines to check that they adhere to
the nf-core community guidelines.

<h2 id="nf_core.lint.run_linting">run_linting</h2>

```python
run_linting(pipeline_dir, release_mode=False)
```
Runs all nf-core linting checks on a given Nextflow pipeline project
in either `release` mode or `normal` mode (default). Returns an object
of type `PipelineLint` after finished.

__Arguments__

- __pipeline_dir (str)__: The path to the Nextflow pipeline root directory
- __release_mode (bool)__: Set this to `True`, if the linting should be run in the `release` mode.
                     See `PipelineLint` for more information.

__Returns__

`PipelineLint`: Contains all the linting results.

<h2 id="nf_core.lint.PipelineLint">PipelineLint</h2>

```python
PipelineLint(self, path)
```
Object to hold linting information and results.
All objects attributes are set, after the `PipelineLint.lint_pipeline()` function was called.

__Dictionary specifications:__

* `conda_config`:
    ```python
         {
            'name': 'nf-core-hlatyping',
            'channels': ['bioconda', 'conda-forge'],
            'dependencies': ['optitype=1.3.2', 'yara=0.9.6']
          }
     ```
* `conda_package_info`:
    See [bioconda-utils](https://api.anaconda.org/package/bioconda/bioconda-utils) as an example.
    ```python
       {
        <package>: <API JSON repsonse object>
       }
    ```
* `config`: Produced by calling Nextflow with `nextflow config -flat <workflow dir>`. Here is an example from
    the nf-core/hlatyping pipeline:
    ```python
        params.container = 'nfcore/hlatyping:1.1.1'
        params.help = false
        params.outdir = './results'
        params.bam = false
        params.singleEnd = false
        params.seqtype = 'dna'
        params.solver = 'glpk'
        params.igenomes_base = './iGenomes'
        params.clusterOptions = false
        ...
    ```

__Attributes__

- `conda_config (dict)`: The parsed conda configuration file content (`environment.yml`).
- `conda_package_info (dict)`: The conda package(s) information, based on the API requests to Anaconda cloud.
- `config (dict)`: The Nextflow pipeline configuration file content.
- `dockerfile (list)`: A list of lines (str) from the parsed Dockerfile.
- `failed (list)`: A list of tuples of the form: `(<error no>, <reason>)`
- `files (list)`: A list of files found during the linting process.
- `minNextflowVersion (str)`: The minimum required Nextflow version to run the pipeline.
- `passed (list)`: A list of tuples of the form: `(<passed no>, <reason>)`
- `path (str)`: Path to the pipeline directory.
- `pipeline_name (str)`: The pipeline name, without the `nf-core` tag, for example `hlatyping`.
- `release_mode (bool)`: `True`, if you the to linting was run in release mode, `False` else.
- `singularityfile (list)`: A list of lines (str) parsed from the Singularity file.
- `warned (list)`: A list of tuples of the form: `(<warned no>, <reason>)`

<h3 id="nf_core.lint.PipelineLint.lint_pipeline">lint_pipeline</h3>

```python
PipelineLint.lint_pipeline(self, release_mode=False)
```
Main linting function.

Takes the pipeline directory as the primary input and iterates through
the different linting checks in order. Collects any warnings or errors
and returns summary at completion. Raises an exception if there is a
critical error that makes the rest of the tests pointless (eg. no
pipeline script). Results from this function are printed by the main script.

Args:
    pipeline_dir (str): The path to the pipeline directory

Returns:
    dict: Summary of test result messages structured as follows:
    {
        'pass': [
            ( test-id (int), message (string) ),
            ( test-id (int), message (string) )
        ],
        'warn': [(id, msg)],
        'fail': [(id, msg)],
    }

Raises:
    If a critical problem is found, an AssertionError is raised.

<h3 id="nf_core.lint.PipelineLint.check_files_exist">check_files_exist</h3>

```python
PipelineLint.check_files_exist(self)
```
Check a given pipeline directory for required files.

Throws an AssertionError if neither nextflow.config or main.nf found
Gives either test failures or warnings for set of other filenames

<h3 id="nf_core.lint.PipelineLint.check_docker">check_docker</h3>

```python
PipelineLint.check_docker(self)
```
Check that Dockerfile contains the string 'FROM '
<h3 id="nf_core.lint.PipelineLint.check_singularity">check_singularity</h3>

```python
PipelineLint.check_singularity(self)
```
Check that Singularity file contains the string 'FROM '
<h3 id="nf_core.lint.PipelineLint.check_licence">check_licence</h3>

```python
PipelineLint.check_licence(self)
```
Check licence file is MIT

Ensures that Licence file is long enough (4 or more lines)
Checks that licence contains the string 'without restriction'
Checks that licence doesn't have any placeholder variables

<h3 id="nf_core.lint.PipelineLint.check_nextflow_config">check_nextflow_config</h3>

```python
PipelineLint.check_nextflow_config(self)
```
Check a given pipeline for required config variables.

Uses `nextflow config -flat` to parse pipeline nextflow.config
and print all config variables.
NB: Does NOT parse contents of main.nf / nextflow script

<h3 id="nf_core.lint.PipelineLint.check_ci_config">check_ci_config</h3>

```python
PipelineLint.check_ci_config(self)
```
Check that the Travis or Circle CI YAML config is valid

Makes sure that `nf-core lint` runs in travis tests
Checks that tests run with the required nextflow version

<h3 id="nf_core.lint.PipelineLint.check_readme">check_readme</h3>

```python
PipelineLint.check_readme(self)
```
Check the repository README file for errors

Currently just checks the badges at the top of the README

<h3 id="nf_core.lint.PipelineLint.check_version_consistency">check_version_consistency</h3>

```python
PipelineLint.check_version_consistency(self)
```
Check container tags versions

Runs on process.container, params.container and $TRAVIS_TAG (each only if set)
Check that the container has a tag
Check that the version numbers are numeric
Check that the version numbers are the same as one-another
<h3 id="nf_core.lint.PipelineLint.check_conda_env_yaml">check_conda_env_yaml</h3>

```python
PipelineLint.check_conda_env_yaml(self)
```
Check that the conda environment file is valid

Make sure that a name is given and is consistent with the pipeline name
Check that depedency versions are pinned
Warn if dependency versions are not the latest available
<h3 id="nf_core.lint.PipelineLint.check_anaconda_package">check_anaconda_package</h3>

```python
PipelineLint.check_anaconda_package(self, dep)
```
Call the anaconda API to find details about package
<h3 id="nf_core.lint.PipelineLint.check_pip_package">check_pip_package</h3>

```python
PipelineLint.check_pip_package(self, dep)
```
Call the PyPI API to find details about package
<h3 id="nf_core.lint.PipelineLint.check_conda_dockerfile">check_conda_dockerfile</h3>

```python
PipelineLint.check_conda_dockerfile(self)
```
Check that the Docker build file looks right, if working with conda

Make sure that a name is given and is consistent with the pipeline name
Check that depedency versions are pinned
Warn if dependency versions are not the latest available
<h3 id="nf_core.lint.PipelineLint.check_conda_singularityfile">check_conda_singularityfile</h3>

```python
PipelineLint.check_conda_singularityfile(self)
```
Check that the Singularity build file looks right, if working with conda

Make sure that a name is given and is consistent with the pipeline name
Check that depedency versions are pinned
Warn if dependency versions are not the latest available
