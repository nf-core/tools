process MOCK_DSL2_APPTAINER_VAR2 {
    label 'process_fake'

    conda "bioconda::dsltwoapptainervartwo=1.1.0"
    container "${['singularity', 'apptainer'].contains(workflow.containerEngine) && !task.ext.singularity_pull_docker_container
        ? 'https://depot.galaxyproject.org/singularity/dsltwoapptainervartwo:1.1.0--hdfd78af_0'
        : 'biocontainers/dsltwoapptainervartwo:1.1.0--hdfd78af_0'}"

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
