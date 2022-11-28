#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { {{ subworkflow_name|upper }} } from '../../../../subworkflows/{{ org }}/{{ subworkflow_dir }}/main.nf'

workflow test_{{ subworkflow_name }} {
    {% if has_meta %}
    input = [
        [ id:'test' ], // meta map
        file(params.test_data['sarscov2']['illumina']['test_paired_end_bam'], checkIfExists: true)
    ]
    {%- else %}
    input = file(params.test_data['sarscov2']['illumina']['test_single_end_bam'], checkIfExists: true)
    {%- endif %}

    {{ subworkflow_name|upper }} ( input )
}
