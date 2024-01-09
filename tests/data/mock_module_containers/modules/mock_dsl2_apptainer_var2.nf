process MOCK {
    label 'process_fake'

    conda "bioconda::dsltwoapptainervartwo=1.1.0"
    container "${ ['singularity', 'apptainer'].contains(workflow.containerEngine) && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/dsltwoapptainervartwo:1.1.0--hdfd78af_0':
        'biocontainers/dsltwoapptainervartwo:1.1.0--hdfd78af_0' }"

    // truncated
}
