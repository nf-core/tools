//
// Mapping
//

include { BOWTIE2_BUILD                             } from '../../modules/nf-core/bowtie2/build/main'
include { FASTQ_ALIGN_BOWTIE2                       } from '../nf-core/fastq_align_bowtie2/main'
include { SAMTOOLS_FAIDX                            } from '../../modules/nf-core/samtools/faidx/main'
include { PIGZ_UNCOMPRESS                           } from '../../modules/nf-core/pigz/uncompress/main'
include { RM_EMPTY_BAM                              } from '../../modules/local/rm_empty_bam/main'
include { RM_EMPTY_BAM as RM_EMPTY_BAM_PATHOGEN     } from '../../modules/local/rm_empty_bam/main'

workflow MAPPING_SHORTREAD {
    take:
    ch_reads_reference // [ [ meta ], [ reads ], [ reference ] ]

    main:
    ch_versions = channel.empty()
    ch_multiqc_files = channel.empty()

    // Build the bowtie2 index
    BOWTIE2_BUILD (
        ch_reads_reference.map { meta, reads, ref -> [ meta, ref ] }
    )
    ch_versions = ch_versions.mix( BOWTIE2_BUILD.out.versions )
    ch_bowtie2_index = BOWTIE2_BUILD.out.index

    // Build the reference index fai
    PIGZ_UNCOMPRESS (
        ch_reads_reference.map { meta, reads, ref -> [ meta, ref ] }
    )
    ch_versions = ch_versions.mix( PIGZ_UNCOMPRESS.out.versions )
    ch_ref_uncompressed = PIGZ_UNCOMPRESS.out.file

    SAMTOOLS_FAIDX ( ch_ref_uncompressed, [ [], [] ], false )
    ch_versions = ch_versions.mix( SAMTOOLS_FAIDX.out.versions )
    ch_fai = SAMTOOLS_FAIDX.out.fai
    ch_ref_fai = ch_ref_uncompressed
        .join(ch_fai, by:0)
    // Join the built index back with the original paired data
    ch_reads_with_index = ch_reads_reference
        .map { meta, reads, ref -> [ meta, reads ] }
        .join(ch_bowtie2_index, by: 0)
        .join(ch_ref_fai, by:0)

    ch_bowtie2_input = ch_reads_with_index
        .multiMap { meta, reads, bowtie2_index, ref, fai ->
            reads: [meta, reads]
            index: [meta, bowtie2_index]
            fasta_fai: [meta, ref, fai]
        }

    // Mapping
    FASTQ_ALIGN_BOWTIE2 (
        ch_bowtie2_input.reads,
        ch_bowtie2_input.index,
        false,                          // save unaligned
        false,                          // sort bam
        ch_bowtie2_input.fasta_fai
    )

    // Remove empty bam files
    if (params.perform_verify_species) {
        FASTQ_ALIGN_BOWTIE2.out.bam
            .collect()
            .map { it -> file("${params.outdir}/mapping/bowtie2/align") }
            .set { ch_bowtie2_align_dir}
        RM_EMPTY_BAM (ch_bowtie2_align_dir)
    }
    if (params.perform_screen_pathogens) {
        FASTQ_ALIGN_BOWTIE2.out.bam
            .collect()
            .map { it -> file("${params.outdir}/pathogens/mapping/bowtie2/align") }
            .set { ch_bowtie2_align_dir}
        RM_EMPTY_BAM_PATHOGEN (ch_bowtie2_align_dir)
    }

    ch_multiqc_files = ch_multiqc_files.mix ( FASTQ_ALIGN_BOWTIE2.out.flagstat.collect{it[1]}.ifEmpty([]) )

    emit:
    index    = BOWTIE2_BUILD.out.index               // channel: [ val(meta), [ index ] ]
    bam      = FASTQ_ALIGN_BOWTIE2.out.bam           // channel: [ val(meta), [ bam ] ]
    bai      = FASTQ_ALIGN_BOWTIE2.out.index           // channel: [ val(meta), [ bai ] ]
    flagstat = FASTQ_ALIGN_BOWTIE2.out.flagstat      // channel: [ val(meta), [ flagstat ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
