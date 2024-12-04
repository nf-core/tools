process UMI_TRANSFER {
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'oras://community.wave.seqera.io/library/umi-transfer:1.0.0--e5b0c1a65b8173b6' :
        'community.wave.seqera.io/library/umi-transfer:1.0.0--d30e8812ea280fa1' }"

        // truncated

}
