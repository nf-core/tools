process MOCK_DSL2_CURRENT {
    label 'process_fake'

    conda "bioconda::dsltwocurrent=1.2.1"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/dsltwocurrent:1.2.1--pyhdfd78af_0'
        : 'biocontainers/dsltwocurrent:1.2.1--pyhdfd78af_0'}"

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
