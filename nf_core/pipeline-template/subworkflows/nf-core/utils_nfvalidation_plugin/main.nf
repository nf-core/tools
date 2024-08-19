//
// Subworkflow that uses the nf-validation plugin to render help text and parameter summary
//

/*
========================================================================================
    IMPORT NF-VALIDATION PLUGIN
========================================================================================
*/

include { paramsSummaryLog   } from 'plugin/nf-schema'
include { validateParameters } from 'plugin/nf-schema'

/*
========================================================================================
    SUBWORKFLOW DEFINITION
========================================================================================
*/

workflow UTILS_NFVALIDATION_PLUGIN {

    take:
    validate_params  // boolean: validate parameters

    main:

    log.debug "Using schema file: ${schema_filename}"

    // Default values for strings
    pre_help_text    = pre_help_text    ?: ''
    post_help_text   = post_help_text   ?: ''
    workflow_command = workflow_command ?: ''

    //
    // Validate parameters relative to the parameter JSON schema
    //
    if (validate_params){
        validateParameters()
    }

    emit:
    dummy_emit = true
}
