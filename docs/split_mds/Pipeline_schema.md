## Pipeline schema

nf-core pipelines have a `nextflow_schema.json` file in their root which describes the different parameters used by the workflow.
These files allow automated validation of inputs when running the pipeline, are used to generate command line help and can be used to build interfaces to launch pipelines.
Pipeline schema files are built according to the [JSONSchema specification](https://json-schema.org/) (Draft 7).

To help developers working with pipeline schema, nf-core tools has three `schema` sub-commands:

* `nf-core schema validate`
* `nf-core schema build`
* `nf-core schema lint`

### Validate pipeline parameters

Nextflow can take input parameters in a JSON or YAML file when running a pipeline using the `-params-file` option.
This command validates such a file against the pipeline schema.

Usage is `nf-core schema validate <pipeline> <parameter file>`, eg:

```console
$ nf-core schema validate rnaseq nf-params.json

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2



INFO     Using local workflow: nf-core/rnaseq (v3.0)
INFO     [✓] Default parameters look valid
INFO     [✓] Pipeline schema looks valid (found 85 params)
INFO     [✓] Input parameters look valid
```

The `pipeline` option can be a directory containing a pipeline, a path to a schema file or the name of an nf-core pipeline (which will be downloaded using `nextflow pull`).

### Build a pipeline schema

Manually building JSONSchema documents is not trivial and can be very error prone.
Instead, the `nf-core schema build` command collects your pipeline parameters and gives interactive prompts about any missing or unexpected params.
If no existing schema is found it will create one for you.

Once built, the tool can send the schema to the nf-core website so that you can use a graphical interface to organise and fill in the schema.
The tool checks the status of your schema on the website and once complete, saves your changes locally.

Usage is `nf-core schema build -d <pipeline_directory>`, eg:

```console
$ nf-core schema build nf-core-testpipeline

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

  INFO     [✓] Default parameters look valid
  INFO     [✓] Pipeline schema looks valid (found 25 params)
❓ Unrecognised 'params.old_param' found in schema but not pipeline! Remove it? [y/n]: y
❓ Unrecognised 'params.we_removed_this_too' found in schema but not pipeline! Remove it? [y/n]: y
✨ Found 'params.input' in pipeline but not in schema. Add to pipeline schema? [y/n]: y
✨ Found 'params.outdir' in pipeline but not in schema. Add to pipeline schema? [y/n]: y
  INFO     Writing schema with 25 params: 'nf-core-testpipeline/nextflow_schema.json'
🚀 Launch web builder for customisation and editing? [y/n]: y
  INFO: Opening URL: https://nf-co.re/pipeline_schema_builder?id=1234567890_abc123def456
  INFO: Waiting for form to be completed in the browser. Remember to click Finished when you're done.
  INFO: Found saved status from nf-core JSON Schema builder
  INFO: Writing JSON schema with 25 params: nf-core-testpipeline/nextflow_schema.json
```

There are four flags that you can use with this command:

* `--dir <pipeline_dir>`: Specify a pipeline directory other than the current working directory
* `--no-prompts`: Make changes without prompting for confirmation each time. Does not launch web tool.
* `--web-only`: Skips comparison of the schema against the pipeline parameters and only launches the web tool.
* `--url <web_address>`: Supply a custom URL for the online tool. Useful when testing locally.

### Linting a pipeline schema

The pipeline schema is linted as part of the main pipeline `nf-core lint` command,
however sometimes it can be useful to quickly check the syntax of the JSONSchema without running a full lint run.

Usage is `nf-core schema lint <schema>`, eg:

```console
$ nf-core schema lint nextflow_schema.json

                                          ,--./,-.
          ___     __   __   __   ___     /,-._.--~\
    |\ | |__  __ /  ` /  \ |__) |__         }  {
    | \| |       \__, \__/ |  \ |___     \`-._,-`-,
                                          `._,._,'

    nf-core/tools version 2.2

  ERROR    [✗] Pipeline schema does not follow nf-core specs:
            Definition subschema 'input_output_options' not included in schema 'allOf'
```
