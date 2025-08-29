process FILTER_BLAST {
    tag "${meta.id}"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/pandas:2.2.1'
        : 'biocontainers/pandas:2.2.1'}"

    input:
    tuple val(meta), path(blast_hits)
    path header

    output:
    tuple val(meta), path('*_filtered.txt')        , emit: filtered_blast, optional: true
    tuple val(meta), path('*_summary.txt')         , emit: summary       , optional: true
    path "versions.yml"                            , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"

    """
    filter_blast.py \\
        --header ${header} \\
        --input ${blast_hits} \\
        --filtered_output ${prefix}_filtered.txt \\
        --summary_output ${prefix}_filtered_summary.txt \\
        ${args}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$( python --version | sed -e 's/Python //g')
    END_VERSIONS

    """
}
