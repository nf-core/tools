//
// Screen pathogens for long reads
//

include { MINIMAP2_INDEX             } from '../../modules/nf-core/minimap2/index/main'
include { MINIMAP2_ALIGN             } from '../../modules/nf-core/minimap2/align/main'
include { BAM_SORT_STATS_SAMTOOLS    } from '../nf-core/bam_sort_stats_samtools/main'

workflow MAPPING_LONGREAD {
    take:
    ch_reads_reference // [ [ meta ], [ reads ], [ reference ] ]

    main:
    ch_versions       = channel.empty()
    ch_multiqc_files  = channel.empty()

    // Build the index
    MINIMAP2_INDEX (
        ch_reads_reference.map { meta, reads, ref -> [ meta, ref ] }
    )
    ch_versions = ch_versions.mix( MINIMAP2_INDEX.out.versions )

    // Join the built index back with the original paired data
    ch_reads_with_index = ch_reads_reference
        .map { meta, reads, ref -> [ meta, reads, ref ] }
        .join(MINIMAP2_INDEX.out.index, by: 0)
        .map { meta, reads, ref, index ->
            [ meta, reads, index, ref ]
        }

    // Align
    ch_reads = ch_reads_with_index
        .map { meta, reads, index, ref -> [ meta, reads ] }
    ch_index = ch_reads_with_index
        .map { meta, reads, index, ref -> [ meta, index ] }
    MINIMAP2_ALIGN (
        ch_reads,
        ch_index,
        true,   // bam_format
        'bai',  // bam_index_extension
        false,  // cigar_paf
        false   // cigar_bam
    )
    ch_versions = ch_versions.mix( MINIMAP2_ALIGN.out.versions.first() )

    // Sort and stats
    ch_bam_with_ref = MINIMAP2_ALIGN.out.bam
        .join(
            ch_reads_with_index.map { meta, reads, index, ref -> [ meta, ref ] },
            by: 0
        )
    ch_bam = ch_bam_with_ref
        .map { meta, bam, ref -> [ meta, bam ] }
    ch_ref = ch_bam_with_ref
        .map { meta, bam, ref -> [ meta, ref ] }
    BAM_SORT_STATS_SAMTOOLS (
        ch_bam,
        ch_ref
    )
    ch_versions = ch_versions.mix(BAM_SORT_STATS_SAMTOOLS.out.versions)
    ch_multiqc_files = ch_multiqc_files.mix(BAM_SORT_STATS_SAMTOOLS.out.flagstat.collect{it[1]}.ifEmpty([]))

    emit:
    index    = MINIMAP2_INDEX.out.index              // channel: [ val(meta), [ index ] ]
    bam      = BAM_SORT_STATS_SAMTOOLS.out.bam       // channel: [ val(meta), [ bam ] ]
    bai      = BAM_SORT_STATS_SAMTOOLS.out.bai       // channel: [ val(meta), [ bai ] ]
    flagstat = BAM_SORT_STATS_SAMTOOLS.out.flagstat  // channel: [ val(meta), [ flagstat ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
