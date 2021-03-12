#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { {{ cookiecutter.tool_name_upper }} } from '../../../../software/{{cookiecutter.tool_dir}}/main.nf' addParams( options: [:] )

workflow test_{{ cookiecutter.tool_name }} {
    {% if cookiecutter.has_meta == "yes" %}
    def input = []
    input = [ [ id:'test', single_end:false ], // meta map
              file("${launchDir}/tests/data/bam/test.paired_end.sorted.bam", checkIfExists: true) ]
    {% endif %}
    {% if cookiecutter.has_meta == "no" %}
    def input = file("${launchDir}/tests/data/bam/test.paired_end.sorted.bam", checkIfExists: true)
    {% endif %}

    {{ cookiecutter.tool_name_upper }} ( input )
}