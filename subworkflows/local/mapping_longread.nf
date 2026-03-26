//
// Screen pathogens for long reads
//

include { MINIMAP2_INDEX                            } from '../../modules/nf-core/minimap2/index/main'
include { MINIMAP2_ALIGN                            } from '../../modules/nf-core/minimap2/align/main'
include { BAM_SORT_STATS_SAMTOOLS                   } from '../nf-core/bam_sort_stats_samtools/main'
include { SAMTOOLS_FAIDX                            } from '../../modules/nf-core/samtools/faidx/main'
include { PIGZ_UNCOMPRESS                           } from '../../modules/nf-core/pigz/uncompress/main'
include { RM_EMPTY_BAM                              } from '../../modules/local/rm_empty_bam/main'
include { RM_EMPTY_BAM as RM_EMPTY_BAM_PATHOGEN     } from '../../modules/local/rm_empty_bam/main'


workflow MAPPING_LONGREAD {
    take:
    ch_reads_reference // [ [ meta ], [ reads ], [ reference ] ]

    main:
    ch_versions       = channel.empty()
    ch_multiqc_files  = channel.empty()

    // Build the minimap2 index
    ch_reference = ch_reads_reference
        .map { meta, reads, ref -> [ meta, ref ] }
    MINIMAP2_INDEX ( ch_reference )
    ch_minimap2_index = MINIMAP2_INDEX.out.index
    ch_versions = ch_versions.mix( MINIMAP2_INDEX.out.versions )

    // Build index fai for the reference
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
        .join(ch_minimap2_index, by: 0)
        .join(ch_ref_fai, by:0)

    ch_minimap_align_input = ch_reads_with_index
        .multiMap { meta, reads, index, ref, fai ->
            ch_reads: [meta, reads]
            ch_minimap2_index: [meta, index]
            ch_ref: [meta, ref, fai]
            }
    // Align
    MINIMAP2_ALIGN (
        ch_minimap_align_input.ch_reads,
        ch_minimap_align_input.ch_minimap2_index,
        true,   // bam_format
        'bai',  // bam_index_extension
        false,  // cigar_paf
        false   // cigar_bam
    )
    ch_versions = ch_versions.mix( MINIMAP2_ALIGN.out.versions.first() )

    // Sort and stats
    ch_bam_ref_fai = MINIMAP2_ALIGN.out.bam
        .join( ch_minimap_align_input.ch_ref, by: 0 )
        .multiMap { meta, bam, ref, fai ->
            ch_bam: [meta, bam]
            ch_ref_fai: [meta, ref, fai]
        }

    BAM_SORT_STATS_SAMTOOLS ( ch_bam_ref_fai.ch_bam, ch_bam_ref_fai.ch_ref_fai )

    // Remove empty bam files
    if (params.perform_verify_species) {
        BAM_SORT_STATS_SAMTOOLS.out.bam
            .collect()
            .map { it -> file("${params.outdir}/mapping/minimap2/align") }
            .set { ch_bowtie2_align_dir}
        RM_EMPTY_BAM (ch_bowtie2_align_dir)
    }
    if (params.perform_screen_pathogens) {
        BAM_SORT_STATS_SAMTOOLS.out.bam
            .collect()
            .map { it -> file("${params.outdir}/pathogens/mapping/minimap2/align") }
            .set { ch_bowtie2_align_dir}
        RM_EMPTY_BAM_PATHOGEN (ch_bowtie2_align_dir)
    }

    ch_multiqc_files = ch_multiqc_files.mix(BAM_SORT_STATS_SAMTOOLS.out.flagstat.collect{it[1]}.ifEmpty([]))

    emit:
    index    = MINIMAP2_INDEX.out.index              // channel: [ val(meta), [ index ] ]
    bam      = BAM_SORT_STATS_SAMTOOLS.out.bam       // channel: [ val(meta), [ bam ] ]
    bai      = BAM_SORT_STATS_SAMTOOLS.out.index       // channel: [ val(meta), [ bai ] ]
    flagstat = BAM_SORT_STATS_SAMTOOLS.out.flagstat  // channel: [ val(meta), [ flagstat ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
