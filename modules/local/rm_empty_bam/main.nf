process RM_EMPTY_BAM {
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/samtools:1.21--h50ea8bc_0' :
        'biocontainers/samtools:1.21--h50ea8bc_0' }"

    input:
    path mapping_folder

    output:
    path folder, optional: true
    tuple val("${task.process}"), val('samtools'), eval('samtools version | sed "1!d;s/.* //"'), emit: versions_samtools, topic: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''

    """
    for bam in ${mapping_folder}/*.bam; do
        if [ -f "\$bam" ]; then
            READ_COUNT=\$(samtools view -c "\$bam")
            if [ "\$READ_COUNT" -eq 0 ]; then
                rm -f "\$bam"
                rm -f "\${bam}.bai"
            fi
        fi
    done

    """
}