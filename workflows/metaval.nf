/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    IMPORT MODULES / SUBWORKFLOWS / FUNCTIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

// Extract reads of taxIDs
include { TAXID_READS                                           } from '../subworkflows/local/taxid_reads'

// De novo for extracted taxIDs reads
include { SPADES                                                } from '../modules/nf-core/spades/main'
include { FLYE                                                  } from '../modules/nf-core/flye/main'

// BLAST
include { SEQKIT_FQ2FA                                          } from '../modules/nf-core/seqkit/fq2fa/main'
include { BLAST                                                 } from '../subworkflows/local/blast.nf'
include { BLAST as BLAST_PATHOGEN                               } from '../subworkflows/local/blast.nf'

// Mapping
include { MAPPING_SHORTREAD                                     } from '../subworkflows/local/mapping_shortread'
include { MAPPING_LONGREAD                                      } from '../subworkflows/local/mapping_longread'
include { MAPPING_SHORTREAD as MAPPING_SHORTREAD_PATHOGEN       } from '../subworkflows/local/mapping_shortread'
include { MAPPING_LONGREAD as MAPPING_LONGREAD_PATHOGEN         } from '../subworkflows/local/mapping_longread'
include { FETCH_BLAST_GENOMES                                   } from '../subworkflows/local/fetch_blast_genomes'
include { IGV as IGV_SHORTREAD                                  } from '../subworkflows/local/igv'
include { IGV as IGV_LONGREAD                                   } from '../subworkflows/local/igv'
include { IGV as IGV_SHORTREAD_PATHOGEN                         } from '../subworkflows/local/igv'
include { IGV as IGV_LONGREAD_PATHOGEN                          } from '../subworkflows/local/igv'

// Calling consensus
include { TAXID_BAM_FASTA as TAXID_BAM_FASTA_SHORTREAD          } from '../subworkflows/local/taxid_bam_fasta'
include { TAXID_BAM_FASTA as TAXID_BAM_FASTA_LONGREAD           } from '../subworkflows/local/taxid_bam_fasta'
include { CONSENSUS                                             } from '../subworkflows/local/consensus'

// Summary subworkflow
include { FASTQC                                                } from '../modules/nf-core/fastqc/main'
include { MULTIQC                                               } from '../modules/nf-core/multiqc/main'
include { paramsSummaryMap                                      } from 'plugin/nf-schema'
include { paramsSummaryMultiqc                                  } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { softwareVersionsToYAML                                } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { methodsDescriptionText                                } from '../subworkflows/local/utils_nfcore_metaval_pipeline'

// Check input path parameters to see if they exist
def checkPathParamList = [ params.input, params.pathogens_genomes,
                            params.accession2taxid,
                            params.blastn_db, params.blast_header,
                            params.blastx_db,params.multiqc_config,
                            params.multiqc_logo, params.multiqc_methods_description
                        ]
for (param in checkPathParamList) { if (param) { file(param, checkIfExists: true) } }

// Check mandatory parameters
if ( params.input ) {
    ch_input              = file(params.input, checkIfExists: true)
} else {
    error("Input samplesheet not specified")
}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    RUN MAIN WORKFLOW
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/

workflow METAVAL {

    take:
    ch_samplesheet // channel: samplesheet read in from --input
    main:

    ch_versions = Channel.empty()
    ch_multiqc_files = Channel.empty()
    ch_fastqc_files = Channel.empty()

    // Create input channels
    ch_input = ch_samplesheet.branch { meta, fastq_1, fastq_2, kraken2_report, kraken2_result, kraken2_taxpasta, centrifuge_report, centrifuge_result, centrifuge_taxpasta, diamond, diamond_taxpasta ->

        // Define single_end based on the conditions
        meta.single_end = ( fastq_1 && !fastq_2 )

        // reads channels
        short_reads: meta.instrument_platform != 'OXFORD_NANOPORE'
            return [ meta, fastq_2 ? [ fastq_1, fastq_2 ] : [ fastq_1 ] ]

        long_reads: meta.instrument_platform == 'OXFORD_NANOPORE'
            return [ meta, [ fastq_1 ] ]
    }

    //
    // Workflow: Extract reads and verification
    //

    // Channels for extracting kraken2/centrifuge/diamond reads
    ch_extract_reads = ch_samplesheet.multiMap { meta, fastq_1, fastq_2, kraken2_report, kraken2_result, kraken2_taxpasta, centrifuge_report, centrifuge_result, centrifuge_taxpasta, diamond, diamond_taxpasta ->
        meta.single_end = ( fastq_1 && !fastq_2 )
        kraken2_taxpasta: [ meta + [ tool: "kraken2" ], kraken2_taxpasta ]
        kraken2_report: [ meta + [ tool: "kraken2" ], kraken2_report ]
        kraken2_result: [ meta, kraken2_result ]
        reads:[ meta, fastq_2 ? [ fastq_1, fastq_2 ] : [ fastq_1 ] ]
        centrifuge_taxpasta: [ meta + [ tool: "centrifuge" ], centrifuge_taxpasta ]
        centrifuge_report: [ meta + [ tool: "centrifuge" ], centrifuge_report ]
        centrifuge_result: [ meta, centrifuge_result ]
        diamond_taxpasta: [ meta + [ tool: "diamond" ], diamond_taxpasta ]
        diamond_tsv: [ meta + [ tool: "diamond" ], diamond ]
    }

    // Verify whether the taxonomic IDs identified by classification are true or false positives.
    if ( params.perform_extract_reads ) {
        //
        // SUBWORKFLOW: TAXID_READS - extract reads
        //
        TAXID_READS (
        ch_extract_reads.reads,
        ch_extract_reads.kraken2_taxpasta,
        ch_extract_reads.kraken2_result,
        ch_extract_reads.kraken2_report,
        ch_extract_reads.centrifuge_taxpasta,
        ch_extract_reads.centrifuge_result,
        ch_extract_reads.centrifuge_report,
        ch_extract_reads.diamond_taxpasta,
        ch_extract_reads.diamond_tsv,
        )
        ch_versions            = ch_versions.mix( TAXID_READS.out.versions )

        // Remove empty FASTQ files. This can happen when users want to check if the same species was identified across different classifiers.
        ch_taxid_reads = TAXID_READS.out.reads
            .branch { it ->
                empty: it[0].single_end ? it[1].countFastq() < 1 : it[1][0].countFastq() < 1 || it[1][1].countFastq() < 1
                nonempty: true
            }

        //
        // MODULE: DE NOVO - SPADES/FLYE
        //

        // Run de novo assembly if the number of reads exceeds the params.min_read_counts
        ch_taxid_reads_filter = ch_taxid_reads.nonempty
            .branch { it ->
                blast: it[0].single_end ? it[1].countFastq() < params.min_read_counts : it[1][0].countFastq() < params.min_read_counts || it[1][1].countFastq() < params.min_read_counts
                denovo: true
            }
        // Prepare de novo assembly reads channel for shortreads and longreads
        ch_denovo = ch_taxid_reads_filter.denovo
            .branch { meta, reads ->
                shortreads: meta.instrument_platform != 'OXFORD_NANOPORE'
                    return [ meta, reads, [], [] ]
                longreads: meta.instrument_platform == 'OXFORD_NANOPORE'
                    return [ meta, reads ]
            }
        // Short reads de novo assembly
        ch_contigs_denovo = Channel.empty()
        if ( params.perform_shortread_denovo ) {
            SPADES( ch_denovo.shortreads, [], [] )
            ch_versions = ch_versions.mix( SPADES.out.versions.first() )
            ch_contigs_denovo = ch_contigs_denovo.mix( SPADES.out.contigs )
        }
        // Long reads de novo assembly
        if ( params.perform_longread_denovo ) {
            FLYE( ch_denovo.longreads, params.flye_mode )
            ch_versions = ch_versions.mix( FLYE.out.versions.first() )
            ch_contigs_denovo = ch_contigs_denovo.mix( FLYE.out.fasta )
        }

        //
        // SUBWORKFLOW: BLAST
        //

        // Prepare the query fasta file
        if ( (!params.skip_blastn) || (!params.skip_blastx)) {
            SEQKIT_FQ2FA ( ch_taxid_reads_filter.blast )
            // Build ch_blast_query fasta file
            ch_blast_query = SEQKIT_FQ2FA.out.fasta
            if ( params.perform_shortread_denovo ) {
                ch_blast_query = ch_blast_query.mix( SPADES.out.contigs )
            }
            if ( params.perform_longread_denovo ) {
                ch_blast_query = ch_blast_query.mix( FLYE.out.fasta )
            }
            ch_versions = ch_versions.mix( SEQKIT_FQ2FA.out.versions.first() )
        }

        BLAST(ch_blast_query, params.blastn_db, params.blastx_db, params.blast_header )
        ch_versions = ch_versions.mix( BLAST.out.versions )

        // Perform FASTQC for reads with BLASTN hits
        ch_fastqc_blastn = ch_taxid_reads.nonempty
            .join( BLAST.out.blastn_filtered, by: 0 )
            .map { meta, reads, filtered_blast -> [ meta, reads ] }

        ch_fastqc_blastx = ch_taxid_reads.nonempty
            .join( BLAST.out.blastx_filtered, by: 0 )
            .map { meta, reads, filtered_blast -> [ meta, reads ] }

        ch_fastqc_files = ch_fastqc_files.mix( ch_fastqc_blastn, ch_fastqc_blastx )

        //
        // SUBWORKFLOW: MAPPING
        //

        if (params.perform_mapping) {
            FETCH_BLAST_GENOMES ( params.taxid2genome, BLAST.out.unique_taxid, ch_taxid_reads.nonempty )

            MAPPING_SHORTREAD ( FETCH_BLAST_GENOMES.out.shortreads, FETCH_BLAST_GENOMES.out.shortreads_genome )
            MAPPING_LONGREAD ( FETCH_BLAST_GENOMES.out.longreads, FETCH_BLAST_GENOMES.out.longreads_genome )
            ch_versions = ch_versions.mix ( MAPPING_SHORTREAD.out.versions )
            ch_versions = ch_versions.mix ( MAPPING_LONGREAD.out.versions )

            //
            // SUBWORKFLOW: IGV
            //
            IGV_SHORTREAD( MAPPING_SHORTREAD.out.bam, MAPPING_SHORTREAD.out.bai, FETCH_BLAST_GENOMES.out.shortreads_genome )
            IGV_LONGREAD( MAPPING_LONGREAD.out.bam, MAPPING_LONGREAD.out.bai, FETCH_BLAST_GENOMES.out.longreads_genome )
            ch_versions = ch_versions.mix ( IGV_SHORTREAD.out.versions )
            ch_versions = ch_versions.mix ( IGV_LONGREAD.out.versions )
        }
    }

    //
    // WORKFLOW: Screen pathogens
    //

    //
    // SUBWORKFLOW: MAPPING
    //
    ch_reference = file( params.pathogens_genomes, checkIfExists: true)

    if ( params.perform_screen_pathogens ) {
        // Map short reads to the pathogens genome
        MAPPING_SHORTREAD_PATHOGEN ( ch_input.short_reads, [ [], ch_reference ] )
        ch_versions = ch_versions.mix( MAPPING_SHORTREAD_PATHOGEN.out.versions )
        ch_multiqc_files = ch_multiqc_files.mix(MAPPING_SHORTREAD_PATHOGEN.out.mqc)
        // Map long reads to the pathogens genome
        MAPPING_LONGREAD_PATHOGEN ( ch_input.long_reads, [ [], ch_reference ] )
        ch_versions = ch_versions.mix( MAPPING_LONGREAD_PATHOGEN.out.versions )
        ch_multiqc_files = ch_multiqc_files.mix(MAPPING_LONGREAD_PATHOGEN.out.mqc)

        // Subset BAM file for each taxID
        ch_accession2taxid = Channel.fromPath ( params.accession2taxid, checkIfExists: true )

        TAXID_BAM_FASTA_SHORTREAD ( MAPPING_SHORTREAD_PATHOGEN.out.bam, MAPPING_SHORTREAD_PATHOGEN.out.bai, ch_accession2taxid, params.min_read_counts )
        ch_versions = ch_versions.mix( TAXID_BAM_FASTA_SHORTREAD.out.versions )

        TAXID_BAM_FASTA_LONGREAD( MAPPING_LONGREAD_PATHOGEN.out.bam, MAPPING_LONGREAD_PATHOGEN.out.bai, ch_accession2taxid, params.min_read_counts )
        ch_versions = ch_versions.mix( TAXID_BAM_FASTA_LONGREAD.out.versions )

        // IGV
        IGV_SHORTREAD_PATHOGEN ( TAXID_BAM_FASTA_LONGREAD.out.taxid_bam, TAXID_BAM_FASTA_LONGREAD.out.taxid_bai, [ [], ch_reference ] )
        IGV_LONGREAD_PATHOGEN ( TAXID_BAM_FASTA_LONGREAD.out.taxid_bam, TAXID_BAM_FASTA_LONGREAD.out.taxid_bai, [ [], ch_reference ] )

        //
        // SUBWORKFLOW: CONSENSUS - BAM file with the number of mapped reads > params.min_read_counts
        //

        ch_bam_filtered = TAXID_BAM_FASTA_SHORTREAD.out.taxid_bam.mix( TAXID_BAM_FASTA_LONGREAD.out.taxid_bam )
        CONSENSUS ( ch_bam_filtered, [ [], ch_reference ], params.consensus_min_bases )

        // BLAST
        // For pair-end reads, only use read1 for BLAST
        ch_shortread_pathogen_blast_read1 = TAXID_BAM_FASTA_SHORTREAD.out.taxid_fasta
            .filter { meta, reads ->
                reads[0].countFasta() >= 1 && reads[1].countFasta() >= 1
            }
            .map { meta, reads -> [ meta, reads[0]] }
        ch_longread_pathogen_blast = TAXID_BAM_FASTA_LONGREAD.out.taxid_fasta
            .filter { meta, reads ->
                reads.countFasta() >= 1
            }
        ch_blast_query_pathogen = ch_shortread_pathogen_blast_read1.mix(
            ch_longread_pathogen_blast,
            CONSENSUS.out.consensus.ifEmpty([])
        )
        BLAST_PATHOGEN ( ch_blast_query_pathogen, params.blastn_db, params.blastx_db, params.blast_header )
        ch_versions = ch_versions.mix( BLAST_PATHOGEN.out.versions )
    }

    //
    // MODULE: FASTQC
    //
        FASTQC( ch_fastqc_files )
        ch_multiqc_files = ch_multiqc_files.mix( FASTQC.out.zip.collect{it[1]} )
        ch_versions = ch_versions.mix( FASTQC.out.versions.first() )

    //
    // Collate and save software versions
    //
    softwareVersionsToYAML(ch_versions)
        .collectFile(
            storeDir: "${params.outdir}/pipeline_info",
            name:  'genomic-medicine-sweden_' + 'metaval_software_'  + 'mqc_'  + 'versions.yml',
            sort: true,
            newLine: true
        ).set { ch_collated_versions }


    //
    // MODULE: MultiQC
    //
    ch_multiqc_config        = Channel.fromPath(
        "$projectDir/assets/multiqc_config.yml", checkIfExists: true)
    ch_multiqc_custom_config = params.multiqc_config ?
        Channel.fromPath(params.multiqc_config, checkIfExists: true) :
        Channel.empty()
    ch_multiqc_logo          = params.multiqc_logo ?
        Channel.fromPath(params.multiqc_logo, checkIfExists: true) :
        Channel.empty()

    summary_params      = paramsSummaryMap(
        workflow, parameters_schema: "nextflow_schema.json")
    ch_workflow_summary = Channel.value(paramsSummaryMultiqc(summary_params))
    ch_multiqc_files = ch_multiqc_files.mix(
        ch_workflow_summary.collectFile(name: 'workflow_summary_mqc.yaml'))
    ch_multiqc_custom_methods_description = params.multiqc_methods_description ?
        file(params.multiqc_methods_description, checkIfExists: true) :
        file("$projectDir/assets/methods_description_template.yml", checkIfExists: true)
    ch_methods_description                = Channel.value(
        methodsDescriptionText(ch_multiqc_custom_methods_description))

    ch_multiqc_files = ch_multiqc_files.mix(ch_collated_versions)
    ch_multiqc_files = ch_multiqc_files.mix(
        ch_methods_description.collectFile(
            name: 'methods_description_mqc.yaml',
            sort: true
        )
    )

    MULTIQC (
        ch_multiqc_files.collect(),
        ch_multiqc_config.toList(),
        ch_multiqc_custom_config.toList(),
        ch_multiqc_logo.toList(),
        [],
        []
    )

    emit:
    multiqc_report = MULTIQC.out.report.toList() // channel: /path/to/multiqc_report.html
    versions       = ch_versions                 // channel: [ path(versions.yml) ]

}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
