process MOCK_DSL2_OLD {
    label 'process_fake'

    conda (params.enable_conda ? "bioconda::dsltwoold=0.23.0" : null)
    if (workflow.containerEngine == 'singularity' && !params.singularity_pull_docker_container) {
        container "https://depot.galaxyproject.org/singularity/dsltwoold:0.23.0--0"
    } else {
        container "quay.io/biocontainers/dsltwoold:0.23.0--0"
    }

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
