


/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW SPECIFIC FOR RNASEQ
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

// TODO nf-core: Update the following workflow to a specific pipeline
workflow SAMPLESHEET_RNASEQ {
    take:
    ch_reads
    format

    main:

    //TODO nf-core: customise to your needs
    ch_list_for_samplesheet = ch_reads.map { meta, reads ->
        //TODO nf-core: Update the path to the published output directory of the reads
        def out_path     = file(params.outdir).toString() + '/relative/custom/path/'
        def sample       = meta.id
        def fastq_1      = meta.single_end  ? out_path + reads.getName() : out_path + reads[0].getName()
        def fastq_2      = !meta.single_end ? out_path + reads[1].getName() : ""
        def strandedness = "auto"
        [sample: sample, fastq_1: fastq_1, fastq_2: fastq_2, strandedness: strandedness]
    }

    channelToSamplesheet(ch_list_for_samplesheet, "${params.outdir}/downstream_samplesheets/rnaseq", format)
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW SPECIFIC FOR SAREK
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

// TODO nf-core: Update the following workflow to a specific pipeline
workflow SAMPLESHEET_SAREK {
    take:
    ch_reads
    format

    main:

    //TODO nf-core: customise to your needs
    ch_list_for_samplesheet = ch_reads.map { meta, reads ->
        //TODO nf-core: Update the path to the published output directory of the reads
        def out_path     = file(params.outdir).toString() + '/relative/custom/path/'
        def patient      = meta.id
        def sample       = meta.id
        def lane         = ""
        def fastq_1      = meta.single_end  ? out_path + reads.getName() : out_path + reads[0].getName()
        def fastq_2      = !meta.single_end ? out_path + reads[1].getName() : ""
        [ patient: patient, sample: sample, lane: lane, fastq_1: fastq_1, fastq_2: fastq_2 ]
    }

    channelToSamplesheet(ch_list_for_samplesheet, "${params.outdir}/downstream_samplesheets/sarek", format)
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    SUBWORKFLOW CALLING PIPELINE SPECIFIC SAMPLESHEET GENERATION
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow GENERATE_DOWNSTREAM_SAMPLESHEETS {
    take:
    input

    main:
    def downstreampipeline_names = params.generate_pipeline_samplesheets.split(",")

    // TODO nf-coee: Add more pipelines here
    if (downstreampipeline_names.contains('rnaseq')) {
        SAMPLESHEET_RNASEQ(
            input,
            params.generate_pipeline_samplesheets_format
        )
    }

    if (downstreampipeline_names.contains('rnaseq')) {
        SAMPLESHEET_SAREK(
            input,
            params.generate_pipeline_samplesheets_format
        )
    }
}

// Input can be any channel with a dictionary
def channelToSamplesheet(ch_list_for_samplesheet, path, format) {
    def format_sep = [csv: ",", tsv: "\t", txt: "\t"][format]

    def ch_header = ch_list_for_samplesheet

    ch_header
        .first()
        .map { it.keySet().join(format_sep) }
        .concat(ch_list_for_samplesheet.map { it.values().join(format_sep) })
        .collectFile(
            name: "${path}.${format}",
            newLine: true,
            sort: false
        )
}
