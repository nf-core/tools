#!/usr/bin/env nextflow
/*
========================================================================================
                         {{ cookiecutter.name }}
========================================================================================
 {{ cookiecutter.name }} Analysis Pipeline.
 #### Homepage / Documentation
 https://github.com/{{ cookiecutter.name }}
----------------------------------------------------------------------------------------
*/

nextflow.preview.dsl = 2

/*
 * Print help message if required
 */
if (params.help) {
    // TODO nf-core: Update typical command used to run pipeline
    def command = "nextflow run ${workflow.manifest.name} --input samplesheet.csv -profile docker"
    log.info Headers.nf_core(workflow, params.monochrome_logs)
    log.info JSON.params_help("$baseDir/nextflow_schema.json", command)
    exit 0
}

/*
 * Stage config files
 */
ch_multiqc_config = file("$baseDir/assets/multiqc_config.yaml", checkIfExists: true)
ch_multiqc_custom_config = params.multiqc_config ? Channel.fromPath(params.multiqc_config, checkIfExists: true) : Channel.empty()
ch_output_docs = file("$baseDir/docs/output.md", checkIfExists: true)
ch_output_docs_images = file("$baseDir/docs/images/", checkIfExists: true)

/*
 * Validate parameters
 */
if (params.input) { ch_input = file(params.input, checkIfExists: true) } else { exit 1, "Input samplesheet file not specified!" }

/*
 * Reference genomes
 */
// TODO nf-core: Add any reference files that are needed
// NOTE - FOR SIMPLICITY THIS IS NOT USED IN THIS PIPELINE
// EXAMPLE ONLY TO DEMONSTRATE USAGE OF AWS IGENOMES
if (params.genomes && params.genome && !params.genomes.containsKey(params.genome)) {
    exit 1, "The provided genome '${params.genome}' is not available in the iGenomes file. Currently the available genomes are ${params.genomes.keySet().join(", ")}"
}
params.fasta = params.genomes[params.genome]?.fasta
if (params.fasta) { ch_fasta = file(params.fasta, checkIfExists: true) }

/*
 * Check parameters
 */
Checks.aws_batch(workflow, params)          // Check AWS batch settings
Checks.hostname(workflow, params, log)      // Check the hostnames against configured profiles

/*
 * Print parameter summary
 */
// Has the run name been specified by the user?
// this has the bonus effect of catching both -name and --name
run_name = params.name
if (!(workflow.runName ==~ /[a-z]+_[a-z]+/)) {
    run_name = workflow.runName
}
summary = JSON.params_summary(workflow, params, run_name)
log.info Headers.nf_core(workflow, params.monochrome_logs)
log.info summary.collect { k,v -> "${k.padRight(18)}: $v" }.join("\n")
log.info "-\033[2m----------------------------------------------------\033[0m-"

/*
 * Include local pipeline modules
 */
include { OUTPUT_DOCUMENTATION } from './modules/local/output_documentation' params(params)
include { GET_SOFTWARE_VERSIONS } from './modules/local/get_software_versions' params(params)
include { CHECK_SAMPLESHEET; check_samplesheet_paths } from './modules/local/check_samplesheet' params(params)

/*
 * Include nf-core modules
 */
include { FASTQC } from './modules/nf-core/fastqc' params(params)
include { MULTIQC } from './modules/nf-core/multiqc' params(params)

/*
 * Run the workflow
 */
workflow {

    CHECK_SAMPLESHEET(ch_input)
        .splitCsv(header:true, sep:',')
        .map { check_samplesheet_paths(it) }
        .set { ch_raw_reads }

    FASTQC(ch_raw_reads)

    OUTPUT_DOCUMENTATION(
        ch_output_docs,
        ch_output_docs_images)

    GET_SOFTWARE_VERSIONS()

    // MULTIQC(
    //     summary,
    //     fastqc.out,
    //     ch_multiqc_config
    // )
}

/*
 * Send completion email
 */
workflow.onComplete {
    def multiqc_report = []
    Completion.email(workflow, params, summary, run_name, baseDir, multiqc_report, log)
    Completion.summary(workflow, params, log)
}

