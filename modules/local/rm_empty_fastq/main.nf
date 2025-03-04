process RM_EMPTY_FASTQ {

    label 'process_low'

    input:
    path folder

    output:
    path folder, optional: true

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    """
    if [ -d ${folder} ]; then
        for f in ${folder}/*.fastq; do
            if [ ! -s \$f ]; then
                rm \$f
            fi
        done
    else
        echo "Folder ${folder} doesn't exist."
    fi
    """
}
