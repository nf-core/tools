process EXTRACT_VIRAL_TAXID {

    tag "$meta.id"
    label 'process_low'

    input:
    val evalue // e-vaule threshold to filter the diamond report
    tuple val(meta), path(taxpasta_standardised_profile)
    tuple val(meta), path(report) // classification report

    output:
    tuple val(meta), path("*viral_taxids.tsv"), optional:true, emit: viral_taxid

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}_${meta.tool}"

    """
    if grep -qi "virus" $taxpasta_standardised_profile; then
        grep -i "virus" $taxpasta_standardised_profile | cut -f 1 > taxpasta_viral_taxid.txt
        if [[ "${meta.tool}" == "kraken2" || "${meta.tool}" == "centrifuge" ]]; then
            awk -F'\t' '\$3 != 0 {print \$5}' ${report} > detected_taxid.txt
            grep -F -w -f taxpasta_viral_taxid.txt detected_taxid.txt > ${prefix}_viral_taxids.tsv
        elif [[ "${meta.tool}" == "diamond" ]]; then
            awk '\$3 < ${evalue}' ${report} | cut -f 2 | sort | uniq > detected_taxid.txt
            grep -F -w -f taxpasta_viral_taxid.txt detected_taxid.txt | sort | uniq > ${prefix}_viral_taxids.tsv
        fi
    fi
    """
}
