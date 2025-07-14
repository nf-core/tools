process FILTER_CONSENSUS {
    tag "${meta.id}"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/python:3.13'
        : 'biocontainers/python:3.13'}"

    input:
    tuple val(meta), path(consensus)
    val min_bases

    output:
    tuple val(meta), path('*_filtered.fasta') , emit: filtered_consensus, optional: true
    path "versions.yml"                       , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"

    """
    filter_consensus.py \\
        ${consensus} \\
        ${prefix}_filtered.fasta \\
        --min-bases ${min_bases}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        python: \$( python --version | sed -e 's/Python //g')
    END_VERSIONS

    """
}
