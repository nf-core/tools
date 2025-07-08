process MEDAKA_PARALLEL {
    tag "${meta.id}"
    label 'process_high'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/89/896f0302268502e1588c34048c6aada1abc64b289b5877701a7014f7ffdf4d20/data' :
        'community.wave.seqera.io/library/medaka:2.0.1--c15f6748e3c63d63' }"

    input:
    tuple val(meta), path(reads), path(assembly)

    output:
    tuple val(meta), path("*.fa.gz"), emit: assembly
    path "versions.yml", emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args1 = task.ext.args1 ?: ''
    def args2 = task.ext.args2 ?: ''
    def args3 = task.ext.args3 ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    mkdir -p tmp
    export TMPDIR=./tmp

    assembly=${assembly}
    if [[ ${assembly} == *.gz ]]; then
        gunzip ${assembly}
        assembly=\$(basename \$assembly .gz)
    fi

    mini_align \\
        -i ${reads} \\
        -r \$assembly \\
        -m \\
        -t $task.cpus \\
        -p ${prefix}_calls_to_draft \\
        ${args1}

    # In medaka >= 2.0 this step is medaka inference, in earlier versions it is consensus
    mkdir inference
    # Start with the largest contigs, they probably take longest
            # Medaka can do with 2 threads and may need some extra for IO

    sort -nrk2 \${assembly}.fai \\
        | cut -f1 | xargs -P ${task.cpus} \\
        -n1 \\
        -I{} \\
        medaka inference ${prefix}_calls_to_draft.bam \\
            inference/{}.hdf \\
            --region {} \\
            --threads 2 \\
            ${args2}

    # In medaka >= 2.0 this step is medaka sequence, in earlier versions it is stitch
    medaka sequence \\
        --threads ${task.cpus} \\
        ${args3} \\
        inference/*.hdf \$assembly ${prefix}.fa

    gzip -n ${prefix}.fa

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        medaka: \$( medaka --version 2>&1 | sed 's/medaka //g' )
    END_VERSIONS
    """
}
