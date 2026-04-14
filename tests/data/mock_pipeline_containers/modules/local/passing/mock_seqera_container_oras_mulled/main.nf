process MOCK_SEQERA_CONTAINER_ORAS_MULLED {
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'oras://community.wave.seqera.io/library/umi-transfer_umicollapse:796a995ff53da9e3'
        : 'community.wave.seqera.io/library/umi-transfer_umicollapse:3298d4f1b49e33bd'}"

    input:
    val mock_val

    output:
    path "*mockery.md", emit: report

    when:
    task.ext.when == null || task.ext.when

    script:
    """
    touch mockery.md
    """
}
