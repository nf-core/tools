//
// Subworkflow with functionality specific to the {{ name }} pipeline
//

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT FUNCTIONS / MODULES / SUBWORKFLOWS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

{% if nf_schema %}include { paramsHelp                } from 'plugin/nf-schema'
include { paramsSummaryLog          } from 'plugin/nf-schema'
include { paramsSummaryMap          } from 'plugin/nf-schema'
include { samplesheetToList         } from 'plugin/nf-schema'
include { validateParameters        } from 'plugin/nf-schema'{% endif %}
include { checkCondaChannels        } from 'plugin/nf-core-utils'
include { checkConfigProvided       } from 'plugin/nf-core-utils'
include { checkProfileProvided      } from 'plugin/nf-core-utils'
{%- if email %}
include { completionEmail           } from 'plugin/nf-core-utils'
{%- endif %}
include { completionSummary         } from 'plugin/nf-core-utils'
include { dumpParametersToJSON      } from 'plugin/nf-core-utils'
include { getWorkflowVersion        } from 'plugin/nf-core-utils'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW TO INITIALISE PIPELINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow PIPELINE_INITIALISATION {

    take:
    version           // boolean: Display version and exit
    {%- if nf_schema %}
    validate_params   // boolean: Boolean whether to validate parameters against the schema at runtime
    monochrome_logs   // boolean: Do not use coloured log outputs
    {%- endif %}
    nextflow_cli_args //   array: List of positional nextflow CLI args
    outdir            //  string: The output directory where the results will be saved
    input             //  string: Path to input samplesheet
    parameters        //     map: Pipeline parameters to dump to JSON
    {%- if nf_schema %}
    help              // boolean: Display help message and exit
    help_full         // boolean: Show the full help message
    show_hidden       // boolean: Show hidden parameters in the help message
    {%- endif %}

    main:

    ch_versions = channel.empty()

    //
    // Print version and exit if required
    //
    if (version) {
        log.info("${workflow.manifest.name} ${getWorkflowVersion()}")
        System.exit(0)
    }

    //
    // Dump pipeline parameters to a JSON file
    //
    if (outdir) {
        dumpParametersToJSON(outdir, parameters)
    }

    //
    // When running with Conda, warn if channels have not been set-up appropriately
    //
    if (workflow.profile.tokenize(',').intersect(['conda', 'mamba']).size() >= 1) {
        checkCondaChannels()
    }

    {%- if nf_schema %}

    //
    // Validate parameters and generate parameter summary to stdout
    //

    def before_text = ""
    def after_text = ""
    {%- if is_nfcore %}
    before_text = """
-\033[2m----------------------------------------------------\033[0m-
                                        \033[0;32m,--.\033[0;30m/\033[0;32m,-.\033[0m
\033[0;34m        ___     __   __   __   ___     \033[0;32m/,-._.--~\'\033[0m
\033[0;34m  |\\ | |__  __ /  ` /  \\ |__) |__         \033[0;33m}  {\033[0m
\033[0;34m  | \\| |       \\__, \\__/ |  \\ |___     \033[0;32m\\`-._,-`-,\033[0m
                                        \033[0;32m`._,._,\'\033[0m
\033[0;35m  {{ name }} ${workflow.manifest.version}\033[0m
-\033[2m----------------------------------------------------\033[0m-
"""
    after_text = """${workflow.manifest.doi ? "\n* The pipeline\n" : ""}${workflow.manifest.doi.tokenize(",").collect { doi -> "    https://doi.org/${doi.trim().replace('https://doi.org/','')}"}.join("\n")}${workflow.manifest.doi ? "\n" : ""}
* The nf-core framework
    https://doi.org/10.1038/s41587-020-0439-x

* Software dependencies
    https://github.com/{{ name }}/blob/{{ default_branch }}/CITATIONS.md
"""
    {%- endif %}
    if (monochrome_logs) {
        before_text = before_text.replaceAll(/\033\[[0-9;]*m/, '')
    }

    def command = "nextflow run ${workflow.manifest.name} -profile <docker/singularity/.../institute> --input samplesheet.csv --outdir <OUTDIR>"

    if (help || help_full) {
        log.info(paramsHelp(
            [
                beforeText: before_text,
                afterText: after_text,
                command: command,
                showHidden: show_hidden,
                fullHelp: help_full,
            ],
            (help instanceof String && help != "true") ? help : "",
        ))
        System.exit(0)
    }

    log.info(before_text)
    log.info(paramsSummaryLog(workflow))
    log.info(after_text)

    if (validate_params) {
        validateParameters()
    }
    {%- endif %}

    //
    // Check config provided to the pipeline
    //
    checkConfigProvided()
    checkProfileProvided(nextflow_cli_args)

    {%- if igenomes %}

    //
    // Custom validation for pipeline parameters
    //
    validateInputParameters()
    {%- endif %}

    //
    // Create channel from input file provided through params.input
    //

    channel{% if nf_schema %}
        .fromList(samplesheetToList(input, "${projectDir}/assets/schema_input.json")){% else %}
        .fromPath(input)
        .splitCsv(header: true, strip: true)
        .map { row ->
            [[id:row.sample], row.fastq_1, row.fastq_2]
        }{% endif %}
        .map {
            meta, fastq_1, fastq_2 ->
                if (!fastq_2) {
                    return [ meta.id, meta + [ single_end:true ], [ fastq_1 ] ]
                } else {
                    return [ meta.id, meta + [ single_end:false ], [ fastq_1, fastq_2 ] ]
                }
        }
        .groupTuple()
        .map { samplesheet ->
            validateInputSamplesheet(samplesheet)
        }
        .map {
            meta, fastqs ->
                return [ meta, fastqs.flatten() ]
        }
        .set { ch_samplesheet }

    emit:
    samplesheet = ch_samplesheet
    versions    = ch_versions
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW FOR PIPELINE COMPLETION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow PIPELINE_COMPLETION {

    take:
    {%- if email %}
    email           //  string: email address
    email_on_fail   //  string: email address sent on pipeline failure
    plaintext_email // boolean: Send plain-text email instead of HTML
    outdir          //    path: Path to output directory where results will be published
    {%- endif %}
    monochrome_logs // boolean: Disable ANSI colour codes in log output
    {%- if multiqc %}
    {%- if email %}
    multiqc_report  //  string: Path to MultiQC report{% endif %}
    {%- endif %}

    main:
    {%- if email %}
    {%- if nf_schema %}
    summary_params = paramsSummaryMap(workflow, parameters_schema: "nextflow_schema.json")
    {%- else %}
    summary_params = [:]
    {%- endif %}

    {%- if multiqc %}
    def multiqc_reports = multiqc_report.toList()
    {%- endif %}
    {%- endif %}

    //
    // Completion email and summary
    //
    workflow.onComplete {
        {%- if email %}
        if (email || email_on_fail) {
            completionEmail(
                summary_params,
                email,
                email_on_fail,
                plaintext_email,
                outdir,
                monochrome_logs,
                {% if multiqc %}multiqc_reports.isBound() ? multiqc_reports.getVal() : [],{% else %}[]{% endif %}
            )
        }
        {%- endif %}

        completionSummary(monochrome_logs)

    }

    workflow.onError {
        log.error "Pipeline failed. Please refer to troubleshooting docs for common issues: https://nf-co.re/docs/running/troubleshooting"
    }
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

{%- if igenomes %}
//
// Check and validate pipeline parameters
//
def validateInputParameters() {
    genomeExistsError()
}
{%- endif %}

//
// Validate channels from input samplesheet
//
def validateInputSamplesheet(input) {
    def (metas, fastqs) = input[1..2]

    // Check that multiple runs of the same sample are of the same datatype i.e. single-end / paired-end
    def endedness_ok = metas.collect{ meta -> meta.single_end }.unique().size == 1
    if (!endedness_ok) {
        error("Please check input samplesheet -> Multiple runs of a sample must be of the same datatype i.e. single-end or paired-end: ${metas[0].id}")
    }

    return [ metas[0], fastqs ]
}

{%- if igenomes %}
//
// Exit pipeline if incorrect --genome key provided
//
def genomeExistsError() {
    if (params.genomes && params.genome && !params.genomes.containsKey(params.genome)) {
        def error_string = "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n" +
            "  Genome '${params.genome}' not found in any config files provided to the pipeline.\n" +
            "  Currently, the available genome keys are:\n" +
            "  ${params.genomes.keySet().join(", ")}\n" +
            "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
        error(error_string)
    }
}
{%- endif %}
