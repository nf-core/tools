process EXTRACT_VIRAL_TAXID {

    tag "${meta.id}"
    label 'process_low'

    input:
    val evalue_threshold // e-value threshold to filter the diamond report
    path phages_taxid // A list of phages taxid to be excluded from the extracted viral taxid
    tuple val(meta), path(taxpasta_standardised_profile), path(report)

    output:
    tuple val(meta), path("*viral_taxids.tsv"), optional: true, emit: viral_taxid

    when:
    task.ext.when == null || task.ext.when

    script:
    def prefix = task.ext.prefix ?: "${meta.id}_${meta.tool}"

    """
    if grep -qi "virus" ${taxpasta_standardised_profile}; then
        grep -i "virus" ${taxpasta_standardised_profile} | cut -f 1,2 > taxpasta_viral_taxid.txt
        #   Replace special characters and space within species name into dash
        awk -F'\t' 'BEGIN{OFS="\t"} {
            gsub(/[^A-Za-z0-9]+/,"-",\$2)
            gsub(/_+/,"-",\$2)
            sub(/^-/,"",\$2)
            sub(/-\$/,"",\$2)
            print \$1,\$2
        }' taxpasta_viral_taxid.txt > taxpasta_viral_taxid_edit.txt

        if [[ "${meta.tool}" == "kraken2" || "${meta.tool}" == "centrifuge" ]]; then
            # Extract all taxids identified in the classification report
            awk -F'\t' '\$3 != 0 {print \$5}' ${report} > detected_taxid.txt
            # Extract only viral taxids found in a given sample
            awk 'NR==FNR{taxid[\$1]=\$2; next} (\$1 in taxid) {print \$1"\t"taxid[\$1]}' taxpasta_viral_taxid_edit.txt detected_taxid.txt > ${prefix}_viral_taxids.tsv
            # Exclude phage taxids
            awk 'NR==FNR{phage[\$1]; next} !(\$1 in phage)' ${phages_taxid} ${prefix}_viral_taxids.tsv > ${prefix}_viral_taxids_nophages.tsv
        elif [[ "${meta.tool}" == "diamond" ]]; then
            awk '\$3 < ${evalue_threshold}' ${report} | cut -f 2 | sort | uniq > detected_taxid.txt
            awk 'NR==FNR{taxid[\$1]=\$2; next} (\$1 in taxid) {print \$1"\t"taxid[\$1]}' taxpasta_viral_taxid_edit.txt detected_taxid.txt > ${prefix}_viral_taxids.tsv
            awk 'NR==FNR{phage[\$1]; next} !(\$1 in phage)' ${phages_taxid} ${prefix}_viral_taxids.tsv > ${prefix}_viral_taxids_nophages.tsv
        fi
    fi
    """
}
