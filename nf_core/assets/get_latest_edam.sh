# Run the following command to update to the latest EDAM file
curl -4 -fsSL https://edamontology.org/EDAM.tsv | \
    awk -F'\t' -v OFS='\t' 'NF>=15 && $15!="" {print $1,$2,$15}' \
    > nf_core/assets/EDAM.tsv
