#!/usr/bin/env nextflow
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    {{ name }}
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Github : https://github.com/{{ name }}
{%- if branded %}
    Website: https://nf-co.re/{{ short_name }}
    Slack  : https://nfcore.slack.com/channels/{{ short_name }}
{%- endif %}
----------------------------------------------------------------------------------------
*/

nextflow.enable.dsl = 2
{% if igenomes %}
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    GENOME PARAMETER VALUES
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

// TODO nf-core: Remove this line if you don't need a FASTA file
//   This is an example of how to use getGenomeAttribute() to fetch parameters
//   from igenomes.config using `--genome`
params.fasta = WorkflowMain.getGenomeAttribute(params, 'fasta')
{% endif %}
/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    VALIDATE & PRINT PARAMETER SUMMARY
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { validateParameters; paramsHelp } from 'plugin/nf-validation'

// Pretty print to terminal
def logo = NfcoreTemplate.logo(workflow, monochrome)
log.info logo
def citation = '\n' + "If you use ${workflow.manifest.name} for your analysis please cite:\n\n" +
    // TODO nf-core: Add Zenodo DOI for pipeline after first release
    //"* The pipeline\n" +
    //"  https://doi.org/10.5281/zenodo.XXXXXXX\n\n" +
    "* The nf-core framework\n" +
    "  https://doi.org/10.1038/s41587-020-0439-x\n\n" +
    "* Software dependencies\n" +
    "  https://github.com/${workflow.manifest.name}/blob/master/CITATIONS.md" + '\n'
log.info citation

// Print help message if needed
if (params.help) {
    def String command = "nextflow run ${workflow.manifest.name} --input samplesheet.csv -profile docker"
    log.info paramsHelp(command)
    System.exit(0)
}

// Validate input parameters
if (params.validate_params) {
    validateParameters()
}

if (params.version) {
    log.info "${workflow.manifest.name}" + getVersion(workflow) + '\n'
    System.exit(0)
}

checkConfigProvided(workflow)

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    NAMED WORKFLOW FOR PIPELINE
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

include { {{ short_name|upper }} } from './workflows/{{ short_name }}'

//
// WORKFLOW: Run main {{ name }} analysis pipeline
//
workflow {{ prefix_nodash|upper }}_{{ short_name|upper }} {
    {{ short_name|upper }} ()
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN ALL WORKFLOWS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

//
// WORKFLOW: Execute a single named workflow for the pipeline
// See: https://github.com/nf-core/rnaseq/issues/619
//
workflow {
    {{ prefix_nodash|upper }}_{{ short_name|upper }} ()
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/


// Create citation string
def createCitation(workflow, monochrome) {

}

// Get version string from manifest and/or git commit
def version(workflow) {
    String version_string = ""

    if (workflow.manifest.version) {
        def prefix_v = workflow.manifest.version[0] != 'v' ? 'v' : ''
        version_string += "${prefix_v}${workflow.manifest.version}"
    }

    if (workflow.commitId) {
        def git_shortsha = workflow.commitId.substring(0, 7)
        version_string += "-g${git_shortsha}"
    }

    return version_string
}

// Check configuration is provided via profiles or custom config
def checkConfigProvided(workflow) {
    if (workflow.profile == 'standard' && workflow.configFiles.size() <= 1) {
        log.warn "[$workflow.manifest.name] You are attempting to run the pipeline without any custom configuration!\n\n" +
            "This will be dependent on your local compute environment but can be achieved via one or more of the following:\n" +
            "   (1) Using an existing pipeline profile e.g. `-profile docker` or `-profile singularity`\n" +
            "   (2) Using an existing nf-core/configs for your Institution e.g. `-profile crick` or `-profile uppmax`\n" +
            "   (3) Using your own local custom config e.g. `-c /path/to/your/custom.config`\n\n" +
            "Please refer to the quick start section and usage docs for the pipeline.\n "
    }
    
    // Check that conda channels are set-up correctly
    if (workflow.profile.tokenize(',').intersect(['conda', 'mamba']).size() >= 1) {
        Utils.checkCondaChannels(log)
    }
}