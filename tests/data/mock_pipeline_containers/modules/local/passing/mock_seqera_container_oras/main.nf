process MOCK_SEQERA_CONTAINER_ORAS {
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6'
        : 'community.wave.seqera.io/library/umi-transfer:1.0.0--d30e8812ea280fa1'}"

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
