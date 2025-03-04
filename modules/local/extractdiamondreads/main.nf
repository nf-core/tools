process EXTRACTCDIAMONDREADS {

    tag "$meta.id"
    label 'process_high'

    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/11/1195d7edbe47145bda13bf6809891dc2fbe9df749c2e567b8879518b8de4ca33/data':
        'community.wave.seqera.io/library/seqkit_python:cf97bbadc3675f5b' }"

    input:
    val taxid
    val evalue
    tuple val (meta), path(tsv)
    tuple val (meta), path(fastq)

    output:
    tuple val(meta), path("*.fastq"), optional: true, emit: extracted_diamond_reads
    path "versions.yml"                             , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    def single_end_flag = meta.single_end ? '--single_end' : ''

    """
    extractdiamondreads.py \\
        --taxid $taxid \\
        --tsv $tsv \\
        --evalue $evalue \\
        --prefix $prefix \\
        $single_end_flag \\
        --fastq ${fastq.join(' ')}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        seqkit: \$( seqkit version | sed -e 's/seqkit v//g' )
        python: \$( python --version | sed -e 's/Python //g')
    END_VERSIONS
    """
}
