process CAT_FASTQ {
    label 'process_single'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data' :
        'community.wave.seqera.io/library/coreutils:9.5--ae99c88a9b28c264' }"

        // truncated

}
