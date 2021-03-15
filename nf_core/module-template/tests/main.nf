#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { {{ tool_name|upper }} } from '../../../{{ "../" if subtool else "" }}software/{{ tool_dir }}/main.nf' addParams( options: [:] )

workflow test_{{ tool_name }} {
    {% if has_meta %}
    def input = []
    input = [ [ id:'test', single_end:false ], // meta map
              file("${launchDir}/tests/data/genomics/sarscov2/bam/test_paired_end.bam", checkIfExists: true) ]
    {%- else %}
    def input = file("${launchDir}/tests/data/genomics/sarscov2/bam/test_single_end.bam", checkIfExists: true)
    {%- endif %}

    {{ tool_name|upper }} ( input )
}
