#!/usr/bin/env nextflow
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    {{ name }}
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Github : https://github.com/{{ name }}
{%- if is_nfcore %}
    Website: https://nf-co.re/{{ short_name }}
    Slack  : https://nfcore.slack.com/channels/{{ short_name }}
{%- endif %}
----------------------------------------------------------------------------------------
*/

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT FUNCTIONS / MODULES / SUBWORKFLOWS / WORKFLOWS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

{%- if workflows_dir %}
include { {{ short_name|upper }}  } from './workflows/{{ short_name }}'
{%- else %}
{%- if modules %}
{% if fastqc %}include { FASTQC                  } from './modules/nf-core/fastqc/main'{% endif %}
{% if multiqc %}include { MULTIQC                 } from './modules/nf-core/multiqc/main'{% endif %}
{% if nf_schema %}include { paramsSummaryMap        } from 'plugin/nf-schema'{% endif %}
{% if multiqc %}include { paramsSummaryMultiqc    } from './subworkflows/nf-core/utils_nfcore_pipeline'{% endif %}
include { softwareVersionsToYAML  } from './subworkflows/nf-core/utils_nfcore_pipeline'
{% if citations or multiqc %}include { methodsDescriptionText  } from './subworkflows/local/utils_nfcore_{{ short_name }}_pipeline'{% endif %}
{%- endif %}
{%- endif %}
{%- if modules %}
include { PIPELINE_INITIALISATION } from './subworkflows/local/utils_nfcore_{{ short_name }}_pipeline'
include { PIPELINE_COMPLETION     } from './subworkflows/local/utils_nfcore_{{ short_name }}_pipeline'
{%- if igenomes %}
include { getGenomeAttribute      } from './subworkflows/local/utils_nfcore_{{ short_name }}_pipeline'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    GENOME PARAMETER VALUES
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

// TODO nf-core: Remove this line if you don't need a FASTA file
//   This is an example of how to use getGenomeAttribute() to fetch parameters
//   from igenomes.config using `--genome`
params.fasta = getGenomeAttribute('fasta')
{% endif %}{% endif %}
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    NAMED WORKFLOWS FOR PIPELINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

//
// WORKFLOW: Run main analysis pipeline depending on type of input
//
workflow {{ prefix_nodash|upper }}_{{ short_name|upper }} {

    take:
    samplesheet // channel: samplesheet read in from --input

{% if workflows_dir %}
    main:
    //
    // WORKFLOW: Run pipeline
    //
    {{ short_name|upper }} (
        samplesheet
    )
{% else %}
    {%- if modules %}
    main:
    ch_versions = Channel.empty()
    {% if multiqc %}ch_multiqc_files = Channel.empty(){% endif %}

    {%- if fastqc %}
    //
    // MODULE: Run FastQC
    //
    FASTQC (
        samplesheet
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
        ch_multiqc_logo.toList()
    )
    {%- endif %}
    {%- endif %}
{%- endif %}
{%- if multiqc %}{%- if modules %}
    emit:
    multiqc_report = {% if workflows_dir %}{{ short_name|upper }}.out.multiqc_report{% else %}MULTIQC.out.report.toList(){% endif %} // channel: /path/to/multiqc_report.html
{%- endif %}{%- endif %}
}
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow {

    main:

    {%- if modules %}
    //
    // SUBWORKFLOW: Run initialisation tasks
    //
    PIPELINE_INITIALISATION (
        params.version,
        params.validate_params,
        params.monochrome_logs,
        args,
        params.outdir,
        params.input
    )
    {% endif %}
    //
    // WORKFLOW: Run main workflow
    //
    {{ prefix_nodash|upper }}_{{ short_name|upper }} (
        {%- if modules %}
        PIPELINE_INITIALISATION.out.samplesheet
        {%- else %}
        params.input
        {%- endif %}
    )

    {%- if modules %}
    //
    // SUBWORKFLOW: Run completion tasks
    //
    PIPELINE_COMPLETION (
        {%- if email %}
        params.email,
        params.email_on_fail,
        params.plaintext_email,
        {%- endif %}
        params.outdir,
        params.monochrome_logs,
        {% if adaptivecard or slackreport %}params.hook_url,{% endif %}
        {% if multiqc %}{{ prefix_nodash|upper }}_{{ short_name|upper }}.out.multiqc_report{% endif %}
    )
    {%- endif %}
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
