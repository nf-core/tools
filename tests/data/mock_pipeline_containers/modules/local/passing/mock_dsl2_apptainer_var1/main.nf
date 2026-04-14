process MOCK_DSL2_APPTAINER_VAR1 {
    label 'process_fake'

    conda "bioconda::dsltwoapptainervarone=1.1.0"
    container "${(workflow.containerEngine == 'singularity' || workflow.containerEngine == 'apptainer') && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/dsltwoapptainervarone:1.1.0--py38h7be5676_2'
        : 'biocontainers/dsltwoapptainervarone:1.1.0--py38h7be5676_2'}"

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
