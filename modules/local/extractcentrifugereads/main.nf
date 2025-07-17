process EXTRACTCENTRIFUGEREADS {

    tag "${meta.id}"
    label 'process_low'

    conda "${moduleDir}/environment.yml"
    container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/35/356ece0aff45ac01c9369c47079609dcbd924d06597a2326804078676300b80b/data'
        : 'community.wave.seqera.io/library/seqkit_pigz:30386cbe834c3ae7'}"

    input:
    val taxid
    tuple val(meta), path(results), path(fastq)

    output:
    tuple val(meta), path("*.fastq.gz"), optional: true, emit: extracted_centrifuge_reads
    path "versions.yml"                                , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    awk -v taxID=${taxid} '\$3 == taxID && \$8 == 1 {print \$1}' ${results} > readID.txt

    if [ -s readID.txt ]; then
        if [ "${meta.single_end}" == 'true' ]; then
            seqkit grep -f readID.txt ${fastq} | pigz -c > ${prefix}_${taxid}.extracted_centrifuge_read.fastq.gz
        else
            seqkit grep -f readID.txt ${fastq[0]} | pigz -c > ${prefix}_${taxid}.extracted_centrifuge_read1.fastq.gz
            seqkit grep -f readID.txt ${fastq[1]} | pigz -c > ${prefix}_${taxid}.extracted_centrifuge_read2.fastq.gz
        fi
    else
        echo "No matching read IDs found for taxid ${taxid}, skipping extraction."
    fi

    rm -f readID.txt

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        seqkit: \$( seqkit version | sed 's/seqkit v//' )
        pigz: \$(pigz --version 2>&1 | sed -e 's/pigz //g')
    END_VERSIONS
    """
}
