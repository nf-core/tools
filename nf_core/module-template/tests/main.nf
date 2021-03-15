#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { {{ tool_name|upper }} } from '../../../../software/{{ tool_dir }}/main.nf' addParams( options: [:] )

workflow test_{{ tool_name }} {
    {% if has_meta %}
    def input = []
    input = [ [ id:'test', single_end:false ], // meta map
              file("${launchDir}/tests/data/bam/test.paired_end.sorted.bam", checkIfExists: true) ]
    {% else %}
    def input = file("${launchDir}/tests/data/bam/test.paired_end.sorted.bam", checkIfExists: true)
    {% endif %}

    {{ tool_name|upper }} ( input )
}
