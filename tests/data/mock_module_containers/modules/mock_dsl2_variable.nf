process STAR_ALIGN {
    // from rnaseq 3.7
    label 'process_fake'

    conda (params.enable_conda ? conda_str : null)
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        "https://depot.galaxyproject.org/singularity/${container_id}" :
        "quay.io/biocontainers/${container_id}" }"


    // Note: 2.7X indices incompatible with AWS iGenomes so use older STAR version
    conda_str = "bioconda::star=2.7.10a bioconda::samtools=1.15.1 conda-forge::gawk=5.1.0"
    container_id = 'mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:afaaa4c6f5b308b4b6aa2dd8e99e1466b2a6b0cd-0'
    if (is_aws_igenome) {
        conda_str = "bioconda::star=2.6.1d bioconda::samtools=1.10 conda-forge::gawk=5.1.0"
        container_id = 'mulled-v2-1fa26d1ce03c295fe2fdcf85831a92fbcbd7e8c2:59cdd445419f14abac76b31dd0d71217994cbcc9-0'
    }

}
