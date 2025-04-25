process RM_EMPTY_FASTQ {

    label 'process_low'

    input:
    path folder

    output:
    path folder, optional: true

    // Consider refactoring this to use conditional logic in the workflow
    when:
    task.ext.when == null || task.ext.when

    script:
    """
    if [ -d "${folder}" ]; then
        for f in "${folder}"/*.fastq.gz; do
            if [ -f "\$f" ]; then
                if [ \$(gzip -dc "\$f" | wc -c) -eq 0 ]; then
                    echo "Removing empty compressed file: \$f"
                    rm "\$f"
                fi
            fi
        done
    else
        echo "Folder ${folder} doesn't exist."
        exit 1
    fi
    """
}
