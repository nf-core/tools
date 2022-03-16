### Launch tool options

* `-r`, `--revision`
    * Specify a pipeline release (or branch / git commit sha) of the project to run
* `-i`, `--id`
    * You can use the web GUI for nf-core pipelines by clicking _"Launch"_ on the website. Once filled in you will be given an ID to use with this command which is used to retrieve your inputs.
* `-c`, `--command-only`
    * If you prefer not to save your inputs in a JSON file and use `-params-file`, this option will specify all entered params directly in the nextflow command.
* `-p`, `--params-in PATH`
    * To use values entered in a previous pipeline run, you can supply the `nf-params.json` file previously generated.
    * This will overwrite the pipeline schema defaults before the wizard is launched.
* `-o`, `--params-out PATH`
    * Path to save parameters JSON file to. (Default: `nf-params.json`)
* `-a`, `--save-all`
    * Without this option the pipeline will ignore any values that match the pipeline schema defaults.
    * This option saves _all_ parameters found to the JSON file.
* `-h`, `--show-hidden`
    * A pipeline JSON schema can define some parameters as 'hidden' if they are rarely used or for internal pipeline use only.
    * This option forces the wizard to show all parameters, including those labelled as 'hidden'.
* `--url`
    * Change the URL used for the graphical interface, useful for development work on the website.