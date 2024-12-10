process UMI_TRANSFER_MULLED {
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'oras://community.wave.seqera.io/library/umi-transfer_umicollapse:796a995ff53da9e3' :
        'community.wave.seqera.io/library/umi-transfer_umicollapse:3298d4f1b49e33bd' }"

        // truncated

}
