/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

{%- if modules %}
{%- if fastqc %}
include { FASTQC                 } from '../modules/nf-core/fastqc/main'{% endif %}
{%- if multiqc %}
include { MULTIQC                } from '../modules/nf-core/multiqc/main'{% endif %}
{%- if nf_schema %}
include { paramsSummaryMap       } from 'plugin/nf-schema'{% endif %}
{%- if multiqc %}
include { paramsSummaryMultiqc   } from '../subworkflows/nf-core/utils_nfcore_pipeline'{% endif %}
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'
{%- if citations or multiqc %}
include { methodsDescriptionText } from '../subworkflows/local/utils_nfcore_{{ short_name }}_pipeline'{% endif %}
{%- endif %}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow {{ short_name|upper }} {

    take:
    ch_samplesheet // channel: samplesheet read in from --input
    {% if multiqc %}
    multiqc_config
    multiqc_logo
    multiqc_methods_description
    {%- endif %}
    outdir

    main:
    {%- if modules %}

    def ch_versions = channel.empty()
    {%- if multiqc %}
    def ch_multiqc_files = channel.empty(){% endif %}

    {%- if fastqc %}
    //
    // MODULE: Run FastQC
    //
    FASTQC(ch_samplesheet)
    {% if multiqc %}ch_multiqc_files = ch_multiqc_files.mix(FASTQC.out.zip.collect{it[1]}){% endif %}
    {%- endif %}

    //
    // Collate and save software versions
    //
    def topic_versions = channel.topic("versions")
        .distinct()
        .branch { entry ->
            versions_file: entry instanceof Path
            versions_tuple: true
        }

    def topic_versions_string = topic_versions.versions_tuple
        .map { process, tool, version ->
            [ process[process.lastIndexOf(':')+1..-1], "  ${tool}: ${version}" ]
        }
        .groupTuple(by:0)
        .map { process, tool_versions ->
            tool_versions.unique().sort()
            "${process}:\n${tool_versions.join('\n')}"
        }

    def ch_collated_versions = softwareVersionsToYAML(ch_versions.mix(topic_versions.versions_file))
        .mix(topic_versions_string)
        .collectFile(
            storeDir: "${outdir}/pipeline_info",
            name: {% if is_nfcore %}'nf_core_'  + {% endif %} '{{ short_name }}_software_' {% if multiqc %} + 'mqc_' {% endif %} + 'versions.yml',
            sort: true,
            newLine: true
        )

{% if multiqc %}
    //
    // MODULE: MultiQC
    //
    ch_multiqc_files = ch_multiqc_files.mix(ch_collated_versions)

    {%- if nf_schema %}
    def ch_summary_params = paramsSummaryMap(workflow, parameters_schema: "nextflow_schema.json")
    def ch_workflow_summary = channel.value(paramsSummaryMultiqc(ch_summary_params))
    ch_multiqc_files = ch_multiqc_files.mix(ch_workflow_summary.collectFile(name: 'workflow_summary_mqc.yaml'))

    {%- endif %}
    {%- if citations %}
    def ch_multiqc_custom_methods_description = multiqc_methods_description
        ? file(multiqc_methods_description, checkIfExists: true)
        : file("${projectDir}/assets/methods_description_template.yml", checkIfExists: true)
    def ch_methods_description = channel.value(methodsDescriptionText(ch_multiqc_custom_methods_description))
    ch_multiqc_files = ch_multiqc_files.mix(ch_methods_description.collectFile(name: 'methods_description_mqc.yaml', sort: true))

    {%- endif %}
    MULTIQC(
        ch_multiqc_files.flatten().collect().map { files ->
            [
                [id: '{{ short_name }}'],
                files,
                multiqc_config
                    ? file(multiqc_config, checkIfExists: true)
                    : file("${projectDir}/assets/multiqc_config.yml", checkIfExists: true),
                multiqc_logo ? file(multiqc_logo, checkIfExists: true) : [],
                [],
                [],
            ]
        }
    )
{% endif %}
    emit:
    {%- if multiqc %}multiqc_report = MULTIQC.out.report.map { _meta, report -> [report] }.toList() // channel: /path/to/multiqc_report.html{% endif %}
    versions       = ch_versions                 // channel: [ path(versions.yml) ]
{%- else %}

    log.info "Nothing to run."
{% endif %}
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
