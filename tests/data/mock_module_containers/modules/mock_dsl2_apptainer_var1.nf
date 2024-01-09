process MOCK {
    label 'process_fake'

    conda "bioconda::dsltwoapptainervarone=1.1.0"
    container "${ (workflow.containerEngine == 'singularity' || workflow.containerEngine == 'apptainer') && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/dsltwoapptainervarone:1.1.0--py38h7be5676_2':
        'biocontainers/dsltwoapptainervarone:1.1.0--py38h7be5676_2' }"

    // truncated
}
