process EXTRACTCENTRIFUGEREADS {

    tag "$meta.id"
    label 'process_low'

    conda "bioconda::seqkit=2.8.2"
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/seqkit:2.8.2--h9ee0642_1':
        'biocontainers/seqkit:2.8.2--h9ee0642_1' }"

    input:
    val taxid
    tuple val (meta), path(results)
    tuple val (meta), path(fastq) // bowtie2/align *unmapped_{1,2}.fastq.gz

    output:
    tuple val(meta), path("*.fastq"), optional:true, emit: extracted_centrifuge_reads
    path "versions.yml"                            , emit: versions

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    """
    awk -v taxID=$taxid '\$3 == taxID && \$8 == 1 {print \$1}' $results > readID.txt
    if [ "${meta.single_end}" == 'true' ]; then
        seqkit grep -f readID.txt $fastq > ${prefix}_${taxid}.extracted_centrifuge_read.fastq
    elif [ "${meta.single_end}" == 'false' ]; then
        seqkit grep -f readID.txt ${fastq[0]} > ${prefix}_${taxid}.extracted_centrifuge_read1.fastq
        seqkit grep -f readID.txt ${fastq[1]} > ${prefix}_${taxid}.extracted_centrifuge_read2.fastq
    fi

    rm readID.txt

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        seqkit: \$( seqkit version | sed 's/seqkit v//' )
    END_VERSIONS
    """
}
