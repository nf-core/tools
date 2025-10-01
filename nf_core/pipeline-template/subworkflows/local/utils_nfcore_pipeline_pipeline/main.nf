//
// Subworkflow with functionality specific to the {{ name }} pipeline
//

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT FUNCTIONS / MODULES / SUBWORKFLOWS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

{% if nf_schema %}include { paramsSummaryLog          } from 'plugin/nf-schema'
include { validateParameters        } from 'plugin/nf-schema'
include { paramsSummaryMap          } from 'plugin/nf-schema'
include { samplesheetToList         } from 'plugin/nf-schema'
include { paramsHelp                } from 'plugin/nf-schema'{% endif %}
{%- if email %}
include { completionEmail           } from 'plugin/nf-core-utils'
{%- endif %}
include { completionSummary         } from 'plugin/nf-core-utils'
{%- if adaptivecard or slackreport %}
include { imNotification            } from 'plugin/nf-core-utils'
{%- endif %}
include { checkConfigProvided       } from 'plugin/nf-core-utils'
include { checkProfileProvided      } from 'plugin/nf-core-utils'
include { getWorkflowVersion        } from 'plugin/nf-core-utils'
include { dumpParametersToJSON      } from 'plugin/nf-core-utils'
include { checkCondaChannels        } from 'plugin/nf-core-utils'
include { processVersionsFromFile   } from 'plugin/nf-core-utils'
include { workflowVersionToChannel  } from 'plugin/nf-core-utils'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW TO INITIALISE PIPELINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow PIPELINE_INITIALISATION {

    take:
    version           // boolean: Display version and exit
    validate_params   // boolean: Boolean whether to validate parameters against the schema at runtime
    monochrome_logs   // boolean: Do not use coloured log outputs
    nextflow_cli_args //   array: List of positional nextflow CLI args
    outdir            //  string: The output directory where the results will be saved
    input             //  string: Path to input samplesheet
    {% if nf_schema %}help              // boolean: Display help message and exit
    help_full         // boolean: Show the full help message
    show_hidden       // boolean: Show hidden parameters in the help message{% endif %}

    main:

    ch_versions = Channel.empty()

    //
    // Print version and exit if required and dump pipeline parameters to JSON file
    //
    if (version) {
        log.info("${workflow.manifest.name} ${getWorkflowVersion(workflow.manifest.version, workflow.commitId)}")
        System.exit(0)
    }

    if (outdir) {
        dumpParametersToJSON(outdir, params)
    }

    if (workflow.profile.tokenize(',').intersect(['conda', 'mamba']).size() >= 1) {
        checkCondaChannels()
    }

    {%- if nf_schema %}

    //
    // Validate parameters and generate parameter summary to stdout
    //
    log.info paramsSummaryLog(workflow)

    if (validate_params) {
        validateParameters()
    }
    {%- endif %}

    //
    // Check config provided to the pipeline
    //
    checkConfigProvided()
    checkProfileProvided(nextflow_cli_args, monochrome_logs)

    {%- if igenomes %}

    //
    // Custom validation for pipeline parameters
    //
    validateInputParameters()
    {%- endif %}

    //
    // Create channel from input file provided through params.input
    //

    Channel{% if nf_schema %}
        .fromList(samplesheetToList(params.input, "${projectDir}/assets/schema_input.json")){% else %}
        .fromPath(params.input)
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
    {%- endif %}
    outdir          //    path: Path to output directory where results will be published
    monochrome_logs // boolean: Disable ANSI colour codes in log output
    {%- if adaptivecard or slackreport %}
    hook_url        //  string: hook URL for notifications{% endif %}
    {%- if multiqc %}
    multiqc_report  //  string: Path to MultiQC report{% endif %}

    main:
    {%- if nf_schema %}
    summary_params = paramsSummaryMap(workflow, parameters_schema: "nextflow_schema.json")
    {%- else %}
    summary_params = [:]
    {%- endif %}

    {%- if multiqc %}
    def multiqc_reports = multiqc_report.toList()
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
                {% if multiqc %}multiqc_reports.getVal(){% else %}[]{% endif %}
            )
        }
        {%- endif %}

        completionSummary(monochrome_logs)

        {%- if adaptivecard or slackreport %}
        if (hook_url) {
            imNotification(summary_params, hook_url)
        }
        {%- endif %}
    }

    workflow.onError {
        log.error "Pipeline failed. Please refer to troubleshooting docs: https://nf-co.re/docs/usage/troubleshooting"
    }
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

//
// Get channel of software versions used in pipeline in YAML format
//
def softwareVersionsToYAML(ch_versions) {
    return ch_versions.unique()
        .map { version -> processVersionsFromFile([version.toString()]) }
        .unique()
        .mix(Channel.fromList(workflowVersionToChannel(workflow.session)).map { it ->
            """
    Workflow:
        ${it[1]}: ${it[2]}
            """.stripIndent().trim()
        })
}

//
// Get workflow summary for MultiQC
//
def paramsSummaryMultiqc(summary_params) {
    def summary_section = ''
    summary_params
        .keySet()
        .each { group ->
            def group_params = summary_params.get(group)
            // This gets the parameters of that particular group
            if (group_params) {
                summary_section += "    <p style=\"font-size:110%\"><b>${group}</b></p>\n"
                summary_section += "    <dl class=\"dl-horizontal\">\n"
                group_params
                    .keySet()
                    .sort()
                    .each { param ->
                        summary_section += "        <dt>${param}</dt><dd><samp>${group_params.get(param) ?: '<span style=\"color:#999999;\">N/A</a>'}</samp></dd>\n"
                    }
                summary_section += "    </dl>\n"
            }
        }

    def yaml_file_text = "id: '${workflow.manifest.name.replace('/', '-')}-summary'\n" as String
    yaml_file_text     += "description: ' - this information is collected when the pipeline is started.'\n"
    yaml_file_text     += "section_name: '${workflow.manifest.name} Workflow Summary'\n"
    yaml_file_text     += "section_href: 'https://github.com/${workflow.manifest.name}'\n"
    yaml_file_text     += "plot_type: 'html'\n"
    yaml_file_text     += "data: |\n"
    yaml_file_text     += "${summary_section}"

    return yaml_file_text
}

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
// Get attribute from genome config file e.g. fasta
//
def getGenomeAttribute(attribute) {
    if (params.genomes && params.genome && params.genomes.containsKey(params.genome)) {
        if (params.genomes[ params.genome ].containsKey(attribute)) {
            return params.genomes[ params.genome ][ attribute ]
        }
    }
    return null
}

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
{%- if citations or multiqc %}
//
// Generate methods description for MultiQC
//
def toolCitationText() {
    // TODO nf-core: Optionally add in-text citation tools to this list.
    // Can use ternary operators to dynamically construct based conditions, e.g. params["run_xyz"] ? "Tool (Foo et al. 2023)" : "",
    // Uncomment function in methodsDescriptionText to render in MultiQC report
    def citation_text = [
            "Tools used in the workflow included:",
            {%- if fastqc %}
            "FastQC (Andrews 2010),",{% endif %}
            {%- if multiqc %}
            "MultiQC (Ewels et al. 2016)",{% endif %}
            "."
        ].join(' ').trim()

    return citation_text
}

def toolBibliographyText() {
    // TODO nf-core: Optionally add bibliographic entries to this list.
    // Can use ternary operators to dynamically construct based conditions, e.g. params["run_xyz"] ? "<li>Author (2023) Pub name, Journal, DOI</li>" : "",
    // Uncomment function in methodsDescriptionText to render in MultiQC report
    def reference_text = [
            {%- if fastqc %}
            "<li>Andrews S, (2010) FastQC, URL: https://www.bioinformatics.babraham.ac.uk/projects/fastqc/).</li>",{% endif %}
            {%- if multiqc %}
            "<li>Ewels, P., Magnusson, M., Lundin, S., & Käller, M. (2016). MultiQC: summarize analysis results for multiple tools and samples in a single report. Bioinformatics , 32(19), 3047–3048. doi: /10.1093/bioinformatics/btw354</li>"{% endif %}
        ].join(' ').trim()

    return reference_text
}

def methodsDescriptionText(mqc_methods_yaml) {
    // Convert  to a named map so can be used as with familiar NXF ${workflow} variable syntax in the MultiQC YML file
    def meta = [:]
    meta.workflow = workflow.toMap()
    meta["manifest_map"] = workflow.manifest.toMap()

    // Pipeline DOI
    if (meta.manifest_map.doi) {
        // Using a loop to handle multiple DOIs
        // Removing `https://doi.org/` to handle pipelines using DOIs vs DOI resolvers
        // Removing ` ` since the manifest.doi is a string and not a proper list
        def temp_doi_ref = ""
        def manifest_doi = meta.manifest_map.doi.tokenize(",")
        manifest_doi.each { doi_ref ->
            temp_doi_ref += "(doi: <a href=\'https://doi.org/${doi_ref.replace("https://doi.org/", "").replace(" ", "")}\'>${doi_ref.replace("https://doi.org/", "").replace(" ", "")}</a>), "
        }
        meta["doi_text"] = temp_doi_ref.substring(0, temp_doi_ref.length() - 2)
    } else meta["doi_text"] = ""
    meta["nodoi_text"] = meta.manifest_map.doi ? "" : "<li>If available, make sure to update the text to include the Zenodo DOI of version of the pipeline used. </li>"

    // Tool references
    meta["tool_citations"] = ""
    meta["tool_bibliography"] = ""

    // TODO nf-core: Only uncomment below if logic in toolCitationText/toolBibliographyText has been filled!
    // meta["tool_citations"] = toolCitationText().replaceAll(", \\.", ".").replaceAll("\\. \\.", ".").replaceAll(", \\.", ".")
    // meta["tool_bibliography"] = toolBibliographyText()


    def methods_text = mqc_methods_yaml.text

    def engine =  new groovy.text.SimpleTemplateEngine()
    def description_html = engine.createTemplate(methods_text).make(meta)

    return description_html.toString()
}
{%- endif %}
