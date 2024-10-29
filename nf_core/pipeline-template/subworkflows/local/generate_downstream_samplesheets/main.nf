//
// Subworkflow with functionality specific to the nf-core/createtaxdb pipeline
//

workflow SAMPLESHEET_RNASEQ {
    take:
    ch_reads

    main:
    format = 'csv'

    ch_list_for_samplesheet = ch_reads.map { meta, db ->
        def tool = meta.tool
        def db_name = meta.id + '-' + meta.tool
        def db_params = ""
        def db_type = ""
        def db_path = file(params.outdir).toString() + '/' + meta.tool + '/' + db.getName()
        [tool: tool, db_name: db_name, db_params: db_params, db_type: db_type, db_path: db_path]
    }

    if (params.build_bracken && params.build_kraken2) {
        log.warn("Generated nf-core/taxprofiler samplesheet will only have a row for bracken. If Kraken2 is wished to be executed separately, duplicate row and update tool column to Kraken2!")
    }

    channelToSamplesheet(ch_list_for_samplesheet, "${params.outdir}/downstream_samplesheets/databases-taxprofiler", format)
}

workflow GENERATE_DOWNSTREAM_SAMPLESHEETS {
    take:
    ch_databases

    main:
    def downstreampipeline_names = params.generate_pipeline_samplesheets.split(",")

    if (downstreampipeline_names.contains('taxprofiler')) {
        SAMPLESHEET_TAXPROFILER(ch_databases)
    }
}

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
