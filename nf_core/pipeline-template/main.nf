#!/usr/bin/env nextflow
/*
========================================================================================
                         {{ name }}
========================================================================================
 {{ name }} Analysis Pipeline.
 #### Homepage / Documentation
 https://github.com/{{ name }}
----------------------------------------------------------------------------------------
*/

nextflow.enable.dsl = 2

////////////////////////////////////////////////////
/* --               PRINT HELP                 -- */
////////////////////////////////////////////////////

log.info Headers.nf_core(workflow, params.monochrome_logs)

def json_schema = "$projectDir/nextflow_schema.json"
if (params.help) {
    // TODO nf-core: Update typical command used to run pipeline
    def command = "nextflow run {{ name }} --input samplesheet.csv --genome GRCh37 -profile docker"
    log.info NfcoreSchema.params_help(workflow, params, json_schema, command)
    exit 0
}

////////////////////////////////////////////////////
/* --        GENOME PARAMETER VALUES           -- */
////////////////////////////////////////////////////

params.fasta = Workflow.get_genome_attribute(params, 'fasta')

////////////////////////////////////////////////////
/* --         PRINT PARAMETER SUMMARY          -- */
////////////////////////////////////////////////////

def summary_params = NfcoreSchema.params_summary_map(workflow, params, json_schema)
log.info NfcoreSchema.params_summary_log(workflow, params, json_schema)

////////////////////////////////////////////////////
/* --         VALIDATE PARAMETERS              -- */
////////////////////////////////////////////////////

Workflow.validate_main_params(workflow, params, json_schema, log)

////////////////////////////////////////////////////
/* --           RUN MAIN WORKFLOW              -- */
////////////////////////////////////////////////////

workflow {
    /*
     * WORKFLOW: main pipeline workflow for {{ name }}
     */
    include { {{ short_name|upper }} } from './workflows/pipeline' addParams( summary_params: summary_params, json_schema: json_schema )
    {{ short_name|upper }} ()
}

////////////////////////////////////////////////////
/* --                  THE END                 -- */
////////////////////////////////////////////////////