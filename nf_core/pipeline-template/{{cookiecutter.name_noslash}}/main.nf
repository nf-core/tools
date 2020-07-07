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
include { print_help; check_genome; check_hostname; check_awsbatch; create_summary; send_email } from './modules/local/functions'
if (params.help) {
    print_help()
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
// NOTE - FOR SIMPLICITY THIS IS NOT USED IN THIS PIPELINE, EXAMPLE ONLY
// If you want to use the channel below in a process, define the following:
//   input:
//   file fasta from ch_fasta
//
params.fasta = params.genomes[params.genome]?.fasta
if (params.fasta) { ch_fasta = file(params.fasta, checkIfExists: true) }

/*
 * Check and print summary for parameters
 */
check_genome()                 // Check if genome exists in the config file
check_hostname()               // Check the hostnames against configured profiles
check_awsbatch()               // Check AWS batch settings
summary = create_summary()     // Print parameter summary

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
    send_email(summary)
}
