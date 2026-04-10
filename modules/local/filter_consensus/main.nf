process FILTER_CONSENSUS {
    tag "${meta.id}"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/python:3.13'
        : 'biocontainers/python:3.13'}"

    input:
    tuple val(meta), path(consensus)
    val consensus_min_bases

    output:
    tuple val(meta), path('*_filtered.fasta') , emit: filtered_consensus, optional: true
    tuple val("${task.process}"), val("python"), eval("python --version | sed -e 's/Python //g'"), emit: versions_python, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"

    """
    filter_consensus.py \\
        ${consensus} \\
        ${prefix}_filtered.fasta \\
        --min-bases ${consensus_min_bases}

    """
}
