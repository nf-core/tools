#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { {{ tool_name|upper }} } from '../../../{{ "../" if subtool else "" }}software/{{ tool_dir }}/main.nf' addParams( options: [:] )

workflow test_{{ tool_name }} {
    {% if has_meta %}
    input = [ [ id:'test', single_end:false ], // meta map
              file(params.test_data['sarscov2']['illumina']['test_paired_end_bam'], checkIfExists: true) ]
    {%- else %}
    input = file(params.test_data['sarscov2']['illumina']['test_single_end_bam'], checkIfExists: true)
    {%- endif %}

    {{ tool_name|upper }} ( input )
}
