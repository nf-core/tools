process MOCK {
    label 'process_fake'
    
    conda     (params.enable_conda ? "bioconda::singlequay=1.9" : null)
    container "quay.io/biocontainers/singlequay:1.9--pyh9f0ad1d_0"

    // truncated
}
