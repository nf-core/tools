process MOCK_NO_CONTAINER {
    label 'process_fake'

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
