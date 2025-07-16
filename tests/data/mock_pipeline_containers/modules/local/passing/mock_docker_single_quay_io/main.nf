process MOCK_DOCKER_SINGLE_QUAY_IO {
    label 'process_fake'

    conda params.enable_conda ? "bioconda::singlequay=1.9" : null
    container "quay.io/biocontainers/singlequay:1.9--pyh9f0ad1d_0"

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
