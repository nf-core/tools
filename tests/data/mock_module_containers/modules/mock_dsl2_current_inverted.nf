process MOCK {
    label 'process_fake'

    conda "bioconda::dsltwocurrentinv=3.3.2"
    container "${ !workflow.containerEngine == 'singularity' && task.ext.singularity_pull_docker_container ?
        'biocontainers/dsltwocurrentinv:3.3.2--h1b792b2_1' :
        'https://depot.galaxyproject.org/singularity/dsltwocurrentinv:3.3.2--h1b792b2_1' }"

    // truncated
}
