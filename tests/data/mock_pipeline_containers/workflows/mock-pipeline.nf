/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
// Mock modules below
include { MOCK_DOCKER_SINGLE_QUAY_IO } from '../modules/local/mock_docker_single_quay_io/main'
include { MOCK_DSL2_APPTAINER_VAR1 } from '../modules/local/mock_dsl2_apptainer_var1/main'
include { MOCK_DSL2_APPTAINER_VAR2 } from '../modules/local/mock_dsl2_apptainer_var2/main'
include { MOCK_DSL2_CURRENT } from '../modules/local/mock_dsl2_current/main'
include { MOCK_DSL2_CURRENT_INVERTED } from '../modules/local/mock_dsl2_current_inverted/main'
include { MOCK_DSL2_OLD } from '../modules/local/mock_dsl2_old/main'
/*
 * It seems that `nextflow inspect` evaluates the container directive before executing any other code in the
 * in the module, so we skip this test for now

// Set up the variable used by the MOCK_DSL2_VARIABLE module
// def is_aws_igenome = false
// include { MOCK_DSL2_VARIABLE } from '../modules/local/mock_dsl2_variable/main'
 */
include { MOCK_SEQERA_CONTAINER_HTTP } from '../modules/local/mock_seqera_container_http/main'
include { MOCK_SEQERA_CONTAINER_ORAS } from '../modules/local/mock_seqera_container_oras/main'
include { MOCK_SEQERA_CONTAINER_ORAS_MULLED } from '../modules/local/mock_seqera_container_oras_mulled/main'
// include { RMARKDOWNNOTEBOOK } from '../modules/nf-core/rmarkdownnotebook/main'

include { paramsSummaryMultiqc } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { softwareVersionsToYAML } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { methodsDescriptionText } from '../subworkflows/local/utils_nfcore_mock-pipeline_pipeline'

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow MOCK_PIPELINE {
    take:
    ch_mockery

    main:

    MOCK_DOCKER_SINGLE_QUAY_IO(ch_mockery)
    MOCK_DSL2_APPTAINER_VAR1(ch_mockery)
    MOCK_DSL2_APPTAINER_VAR2(ch_mockery)
    MOCK_DSL2_CURRENT(ch_mockery)
    MOCK_DSL2_CURRENT_INVERTED(ch_mockery)
    MOCK_DSL2_OLD(ch_mockery)
}
