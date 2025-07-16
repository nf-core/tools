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
include { UNTAR  as UNTAR_BLASTN                                } from '../modules/nf-core/untar/main'
include { UNTAR  as UNTAR_BLASTX                                } from '../modules/nf-core/untar/main'
include { SEQKIT_FQ2FA                                          } from '../modules/nf-core/seqkit/fq2fa/main'
include { BLAST_BLASTN                                          } from '../modules/nf-core/blast/blastn/main'
include { BLAST_BLASTN as BLAST_BLASTN_PATHOGEN                 } from '../modules/nf-core/blast/blastn/main'
include { FILTER_BLAST as FILTER_BLASTN                         } from '../modules/local/filter_blast/main'
include { FILTER_BLAST as FILTER_BLASTN_PATHOGEN                } from '../modules/local/filter_blast/main'
include { DIAMOND_BLASTX                                        } from '../modules/nf-core/diamond/blastx/main'
include { DIAMOND_BLASTX as DIAMOND_BLASTX_PATHOGEN             } from '../modules/nf-core/diamond/blastx/main'
include { FILTER_BLAST as FILTER_BLASTX                         } from '../modules/local/filter_blast/main'
include { FILTER_BLAST as FILTER_BLASTX_PATHOGEN                } from '../modules/local/filter_blast/main'

// Maping subworkflow
include { BOWTIE2_BUILD as BOWTIE2_BUILD_PATHOGEN               } from '../modules/nf-core/bowtie2/build/main'
include { FASTQ_ALIGN_BOWTIE2                                   } from '../subworkflows/nf-core/fastq_align_bowtie2/main'
include { LONGREAD_SCREENPATHOGEN                               } from '../subworkflows/local/longread_screenpathogen'
include { SAMTOOLS_CONSENSUS as SHORTREAD_SAMTOOLS_CONSENSUS    } from '../modules/nf-core/samtools/consensus/main'

// Calling consensus
include { TAXID_BAM_FASTA as TAXID_BAM_FASTA_SHORTREAD          } from '../subworkflows/local/taxid_bam_fasta'
include { TAXID_BAM_FASTA as TAXID_BAM_FASTA_LONGREAD           } from '../subworkflows/local/taxid_bam_fasta'
include { LONGREAD_CONSENSUS                                    } from '../subworkflows/local/longread_consensus'
include { FILTER_CONSENSUS as FILTER_CONSENSUS_SHORTREAD        } from '../modules/local/filter_consensus'
include { FILTER_CONSENSUS as FILTER_CONSENSUS_LONGREAD         } from '../modules/local/filter_consensus'

// Summary subworkflow
include { FASTQC                                                } from '../modules/nf-core/fastqc/main'
include { MULTIQC                                               } from '../modules/nf-core/multiqc/main'
include { paramsSummaryMap                                      } from 'plugin/nf-schema'
include { paramsSummaryMultiqc                                  } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { softwareVersionsToYAML                                } from '../subworkflows/nf-core/utils_nfcore_pipeline'
include { methodsDescriptionText                                } from '../subworkflows/local/utils_nfcore_metaval_pipeline'


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

    // Prepare the blastn database channel
    if ( !params.skip_blastn ) {
        if (params.blastn_db.endsWith('.tar.gz')) {
            UNTAR_BLASTN (
                [ [:],file( params.blastn_db, checkIfExists: true )]
            )
            ch_blastn_db = UNTAR_BLASTN.out.untar
            ch_versions = ch_versions.mix( UNTAR_BLASTN.out.versions )
        } else {
            ch_blastn_db = [ [:], file( params.blastn_db, checkIfExists: true ) ]
        }
    }
    // Prepare the blastx database channel
    if ( !params.skip_blastx ) {
        if (params.blastx_db.endsWith('.tar.gz')) {
            UNTAR_BLASTX (
                [ [:],file( params.blastx_db, checkIfExists: true )]
            )
            ch_blastx_db = UNTAR_BLASTX.out.untar
            ch_versions = ch_versions.mix( UNTAR_BLASTX.out.versions )
        } else {
            ch_blastx_db = [ [:], file( params.blastx_db, checkIfExists: true ) ]
        }
    }
    // Verify whether the taxonomic IDs identified by classification are true or false positives.
    if ( params.perform_extract_reads ) {

        // SUBWORKFLOW: TAXID_READS - extract reads
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
        // MODULE: Run FastQC
        //

        FASTQC (
            ch_taxid_reads.nonempty
        )
        ch_multiqc_files = ch_multiqc_files.mix(FASTQC.out.zip.collect{it[1]})
        ch_versions = ch_versions.mix(FASTQC.out.versions.first())

        // SUBWORKFLOW: DE NOVO
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
        // short reads de novo assembly
        if ( params.perform_shortread_denovo ) {
            SPADES( ch_denovo.shortreads, [], [] )
            ch_versions             = ch_versions.mix( SPADES.out.versions.first() )
        }
        // long reads de novo assembly
        if ( params.perform_longread_denovo ) {
            FLYE( ch_denovo.longreads, params.flye_mode )
            ch_versions             = ch_versions.mix( FLYE.out.versions.first() )
        }

        // BLAST
        // Prepare the query fasta file
        SEQKIT_FQ2FA ( ch_taxid_reads_filter.blast )
        ch_blast_query = SEQKIT_FQ2FA.out.fasta.mix( SPADES.out.contigs, FLYE.out.fasta )
        ch_versions = ch_versions.mix( SEQKIT_FQ2FA.out.versions.first() )
        // BLASTN
        if ( !params.skip_blastn ) {
            BLAST_BLASTN ( ch_blast_query, ch_blastn_db )
            ch_versions = ch_versions.mix( BLAST_BLASTN.out.versions.first() )
            // Filter BLASTN hits
            ch_blastn_hits = BLAST_BLASTN.out.txt
                .filter { meta, blastn_file -> blastn_file.size() > 0 }

            FILTER_BLASTN ( ch_blastn_hits, file( params.blast_header, checkIfExists: true))
            ch_versions = ch_versions.mix( FILTER_BLASTN.out.versions.first() )
        }
        // BLASTX:DIAMOND
        if ( !params.skip_blastx ) {
            DIAMOND_BLASTX (
                ch_blast_query,
                ch_blastx_db,
                'txt',
                'qseqid sseqid slen pident qlen length qcovhsp nident evalue bitscore staxids sscinames' )
            ch_versions = ch_versions.mix( DIAMOND_BLASTX.out.versions.first() )
            // Filter BLASTX hits
            ch_blastx_hits = DIAMOND_BLASTX.out.txt
                .filter { meta, blastx_file -> blastx_file.size() > 0 }
            FILTER_BLASTX ( ch_blastx_hits, file( params.blast_header, checkIfExists: true))
            ch_versions = ch_versions.mix( FILTER_BLASTX.out.versions.first() )
        }
        }

    // Screen pathogens
    ch_reference = file( params.pathogens_genomes, checkIfExists: true)

    if ( params.perform_screen_pathogens ) {
        // Map short reads to the pathogens genome
        BOWTIE2_BUILD_PATHOGEN ( [ [], ch_reference ] )
        ch_versions = ch_versions.mix( BOWTIE2_BUILD_PATHOGEN.out.versions )
        FASTQ_ALIGN_BOWTIE2 (
            ch_input.short_reads,                              // ch_reads
            BOWTIE2_BUILD_PATHOGEN.out.index,                  // ch_index
            false,                                             // save unaligned
            false,                                             // sort bam
            [ [], ch_reference ]
        )
        ch_versions = ch_versions.mix( FASTQ_ALIGN_BOWTIE2.out.versions )
        ch_multiqc_files = ch_multiqc_files.mix (FASTQ_ALIGN_BOWTIE2.out.stats.collect{it[1]}.ifEmpty([]))
        ch_multiqc_files = ch_multiqc_files.mix (FASTQ_ALIGN_BOWTIE2.out.flagstat.collect{it[1]}.ifEmpty([]))
        ch_multiqc_files = ch_multiqc_files.mix (FASTQ_ALIGN_BOWTIE2.out.idxstats.collect{it[1]}.ifEmpty([]))

        // Map long reads to the pathogens genome
        LONGREAD_SCREENPATHOGEN ( ch_input.long_reads, [ [], ch_reference ] )
        ch_versions = ch_versions.mix( LONGREAD_SCREENPATHOGEN.out.versions )
        ch_multiqc_files = ch_multiqc_files.mix(LONGREAD_SCREENPATHOGEN.out.mqc)

        // Subset BAM file for each taxID
        ch_accession2taxid = Channel.fromPath ( params.accession2taxid, checkIfExists: true )

        TAXID_BAM_FASTA_SHORTREAD ( FASTQ_ALIGN_BOWTIE2.out.bam, FASTQ_ALIGN_BOWTIE2.out.bai, ch_accession2taxid, params.min_read_counts )
        ch_versions = ch_versions.mix( TAXID_BAM_FASTA_SHORTREAD.out.versions )

        TAXID_BAM_FASTA_LONGREAD( LONGREAD_SCREENPATHOGEN.out.bam, LONGREAD_SCREENPATHOGEN.out.bai, ch_accession2taxid, params.min_read_counts )
        ch_versions = ch_versions.mix( TAXID_BAM_FASTA_LONGREAD.out.versions )

        // Calling consensus: BAM file with the number of mapped reads > params.min_read_counts
        if (params.perform_shortread_consensus) {
            SHORTREAD_SAMTOOLS_CONSENSUS ( TAXID_BAM_FASTA_SHORTREAD.out.taxid_bam )
            ch_versions = ch_versions.mix(SHORTREAD_SAMTOOLS_CONSENSUS.out.versions)
            // Remove consensus sequences shorter than params.consensus_min_bases (default: 50 bp)
            FILTER_CONSENSUS_SHORTREAD ( SHORTREAD_SAMTOOLS_CONSENSUS.out.fasta, params.consensus_min_bases )
            ch_versions = ch_versions.mix(FILTER_CONSENSUS_SHORTREAD.out.versions)
        }
        if ( params.perform_longread_consensus ) {
            // Skip the consensus calling if the number of mapped reads is lower than params.min_read_counts
            LONGREAD_CONSENSUS ( TAXID_BAM_FASTA_LONGREAD.out.taxid_bam, [ [], ch_reference ] )
            ch_versions = ch_versions.mix( LONGREAD_CONSENSUS.out.versions )
            FILTER_CONSENSUS_LONGREAD ( LONGREAD_CONSENSUS.out.consensus, params.consensus_min_bases)
            ch_versions = ch_versions.mix( FILTER_CONSENSUS_LONGREAD.out.versions )
        }
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
            FILTER_CONSENSUS_SHORTREAD.out.filtered_consensus.ifEmpty([]),
            FILTER_CONSENSUS_LONGREAD.out.filtered_consensus.ifEmpty([])
        )

        if (!params.skip_blastn) {
            // BLASTN
            BLAST_BLASTN_PATHOGEN ( ch_blast_query_pathogen, ch_blastn_db )
            ch_versions = ch_versions.mix( BLAST_BLASTN_PATHOGEN.out.versions.first() )

            // Filter BLASTN hits
            ch_blastn_hits_pathogen = BLAST_BLASTN_PATHOGEN.out.txt
                .filter { meta, blastn_file -> blastn_file.size() > 0 }
            FILTER_BLASTN_PATHOGEN ( ch_blastn_hits_pathogen, file( params.blast_header, checkIfExists: true))
            ch_versions = ch_versions.mix( FILTER_BLASTN_PATHOGEN.out.versions.first() )

        }
        // BLASTX:DIAMOND
        if ( !params.skip_blastx ) {
            DIAMOND_BLASTX_PATHOGEN (
                ch_blast_query_pathogen,
                ch_blastx_db,
                'txt',
                'qseqid sseqid slen pident qlen length qcovhsp nident evalue bitscore staxids sscinames' )
            ch_versions = ch_versions.mix( DIAMOND_BLASTX_PATHOGEN.out.versions.first() )
            // Filter BLASTX hits
            ch_blastx_hits_pathogen = DIAMOND_BLASTX_PATHOGEN.out.txt
                .filter { meta, blastx_file -> blastx_file.size() > 0 }
            FILTER_BLASTX_PATHOGEN ( ch_blastx_hits_pathogen, file( params.blast_header, checkIfExists: true))
            ch_versions = ch_versions.mix( FILTER_BLASTX_PATHOGEN.out.versions.first() )
        }
    }

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

    emit:multiqc_report = MULTIQC.out.report.toList() // channel: /path/to/multiqc_report.html
    versions       = ch_versions                 // channel: [ path(versions.yml) ]

}

/*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    THE END
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*/
