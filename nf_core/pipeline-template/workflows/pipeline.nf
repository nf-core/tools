/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

{%- if modules %}
{% if fastqc %}include { FASTQC                 } from '../modules/nf-core/fastqc/main'{% endif %}
{% if multiqc %}include { MULTIQC                } from '../modules/nf-core/multiqc/main'{% endif %}
{% if nf_schema %}include { paramsSummaryMap       } from 'plugin/nf-schema'{% endif %}
{% if multiqc %}include { paramsSummaryMultiqc   } from '../subworkflows/nf-core/utils_nfcore_pipeline'{% endif %}
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'
{% if citations or multiqc %}include { methodsDescriptionText } from '../subworkflows/local/utils_nfcore_{{ short_name }}_pipeline'{% endif %}
{%- endif %}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow {{ short_name|upper }} {

    take:
    ch_samplesheet // channel: samplesheet read in from --input

    {%- if modules %}
    main:

    ch_versions = Channel.empty()
    {% if multiqc %}ch_multiqc_files = Channel.empty(){% endif %}

    {%- if fastqc %}
    //
    // MODULE: Run FastQC
    //
    FASTQC (
        ch_samplesheet
    )
    {% if multiqc %}ch_multiqc_files = ch_multiqc_files.mix(FASTQC.out.zip.collect{it[1]}){% endif %}
    ch_versions = ch_versions.mix(FASTQC.out.versions.first())
    {%- endif %}

    //
    // Collate and save software versions
    //
    softwareVersionsToYAML(ch_versions)
        .collectFile(
            storeDir: "${params.outdir}/pipeline_info",
            name: {% if is_nfcore %}'nf_core_' {% else %} '' {% endif %} + 'pipeline_software_' + {% if multiqc %} 'mqc_' {% else %} '' {% endif %} + 'versions.yml',
            sort: true,
            newLine: true
        ).set { ch_collated_versions }

{% if multiqc %}
    //
    // MODULE: MultiQC
    //
    ch_multiqc_config        = Channel.fromPath(
        "$projectDir/assets/multiqc_config.yml", checkIfExists: true)
    ch_multiqc_custom_config = params.multiqc_config ?
        Channel.fromPath(params.multiqc_config, checkIfExists: true) :
        Channel.empty()
    ch_multiqc_logo          = params.multiqc_logo ?
        Channel.fromPath(params.multiqc_logo, checkIfExists: true) :
        Channel.empty()

    {% if nf_schema %}
    summary_params      = paramsSummaryMap(
        workflow, parameters_schema: "nextflow_schema.json")
    ch_workflow_summary = Channel.value(paramsSummaryMultiqc(summary_params))
    ch_multiqc_files = ch_multiqc_files.mix(
        ch_workflow_summary.collectFile(name: 'workflow_summary_mqc.yaml'))
    {% endif %}

    {%- if citations %}
    ch_multiqc_custom_methods_description = params.multiqc_methods_description ?
        file(params.multiqc_methods_description, checkIfExists: true) :
        file("$projectDir/assets/methods_description_template.yml", checkIfExists: true)
    ch_methods_description                = Channel.value(
        methodsDescriptionText(ch_multiqc_custom_methods_description))
    {%- endif %}

    ch_multiqc_files = ch_multiqc_files.mix(ch_collated_versions)
    {%- if citations %}
    ch_multiqc_files = ch_multiqc_files.mix(
        ch_methods_description.collectFile(
            name: 'methods_description_mqc.yaml',
            sort: true
        )
    )
    {%- endif %}

    MULTIQC (
        ch_multiqc_files.collect(),
        ch_multiqc_config.toList(),
        ch_multiqc_custom_config.toList(),
        ch_multiqc_logo.toList(),
        [],
        []
    )
{% endif %}
    emit:
    {%- if multiqc %}multiqc_report = MULTIQC.out.report.toList() // channel: /path/to/multiqc_report.html{% endif %}
    versions       = ch_versions                 // channel: [ path(versions.yml) ]
{% endif %}
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
