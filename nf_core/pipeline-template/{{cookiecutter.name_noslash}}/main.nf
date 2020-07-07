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
include 'modules/nf-core/functions' params(params)
if (params.help) {
    print_help()
    exit 0
}

/*
 * Stage and check config files
 */
ch_multiqc_config = file("$baseDir/assets/multiqc_config.yaml", checkIfExists: true)
ch_multiqc_custom_config = params.multiqc_config ? Channel.fromPath(params.multiqc_config, checkIfExists: true) : Channel.empty()
ch_output_docs = file("$baseDir/docs/output.md", checkIfExists: true)
ch_output_docs_images = file("$baseDir/docs/images/", checkIfExists: true)

/*
 * Create a channel for input read files
 */
if (params.input_paths) {
    if (params.single_end) {
        Channel
            .from(params.input_paths)
            .map { row -> [ row[0], [ file(row[1][0], checkIfExists: true) ] ] }
            .ifEmpty { exit 1, "params.input_paths was empty - no input files supplied" }
            .into { ch_read_files_fastqc; ch_read_files_trimming }
    } else {
        Channel
            .from(params.input_paths)
            .map { row -> [ row[0], [ file(row[1][0], checkIfExists: true), file(row[1][1], checkIfExists: true) ] ] }
            .ifEmpty { exit 1, "params.input_paths was empty - no input files supplied" }
            .into { ch_read_files_fastqc; ch_read_files_trimming }
    }
} else {
    Channel
        .fromFilePairs(params.input, size: params.single_end ? 1 : 2)
        .ifEmpty { exit 1, "Cannot find any reads matching: ${params.input}\nNB: Path needs to be enclosed in quotes!\nIf this is single-end data, please specify --single_end on the command line." }
        .into { ch_read_files_fastqc; ch_read_files_trimming }
}

/*
 * Check and print summary for parameters
 */
check_genome()                 // Check if genome exists in the config file
check_hostname()               // Check the hostnames against configured profiles
check_awsbatch()               // Check AWS batch settings
summary = create_summary()     // Print parameter summary

/*
 * FastQC
 */
//include 'modules/nf-core/fastqc' params(params)

/*
 * MultQC
 */
//include 'modules/nf-core/multiqc' params(params)

/*
 * Get software versions
 */
include 'modules/nf-core/get_software_versions' params(params)
get_software_versions()

/*
 * Output markdown documentation as HTML
 */
include 'modules/nf-core/output_documentation' params(params)
output_documentation()

/*
 * Send completion email
 */
workflow.onComplete {
    send_email(summary)
}

// Channel.from(summary.collect{ [it.key, it.value] })
//     .map { k,v -> "<dt>$k</dt><dd><samp>${v ?: '<span style=\"color:#999999;\">N/A</a>'}</samp></dd>" }
//     .reduce { a, b -> return [a, b].join("\n            ") }
//     .map { x -> """
//     id: '{{ cookiecutter.name_noslash }}-summary'
//     description: " - this information is collected when the pipeline is started."
//     section_name: '{{ cookiecutter.name }} Workflow Summary'
//     section_href: 'https://github.com/{{ cookiecutter.name }}'
//     plot_type: 'html'
//     data: |
//         <dl class=\"dl-horizontal\">
//             $x
//         </dl>
//     """.stripIndent() }
//     .set { ch_workflow_summary }
