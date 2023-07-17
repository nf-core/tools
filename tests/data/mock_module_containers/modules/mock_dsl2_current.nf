process MOCK {
    label 'process_fake'

    conda "bioconda::dsltwocurrent=1.2.1"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/dsltwocurrent:1.2.1--pyhdfd78af_0':
        'biocontainers/dsltwocurrent:1.2.1--pyhdfd78af_0' }"

    // truncated
}
