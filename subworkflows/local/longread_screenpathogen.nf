
//
// Screen pathogens for long reads
//

include { MINIMAP2_INDEX             } from '../../modules/nf-core/minimap2/index/main'
include { MINIMAP2_ALIGN             } from '../../modules/nf-core/minimap2/align/main'
include { BAM_SORT_STATS_SAMTOOLS    } from '../nf-core/bam_sort_stats_samtools/main'

workflow LONGREAD_SCREENPATHOGEN {
    take:
    reads     // [ [ meta ], [ reads ] ]
    reference // [ [ meta ], [ reference ] ]

    main:
    ch_versions       = Channel.empty()
    ch_multiqc_files  = Channel.empty()

    ch_minimap2_index = MINIMAP2_INDEX ( reference ).index
    ch_versions       = ch_versions.mix( MINIMAP2_INDEX.out.versions )

    MINIMAP2_ALIGN ( reads, ch_minimap2_index, true, 'bai', false, false )
    ch_versions        = ch_versions.mix( MINIMAP2_ALIGN.out.versions.first() )

    BAM_SORT_STATS_SAMTOOLS ( MINIMAP2_ALIGN.out.bam, reference )
    ch_versions = ch_versions.mix(BAM_SORT_STATS_SAMTOOLS.out.versions)

    emit:
    index    = MINIMAP2_INDEX.out.index              // channel: [ val(meta), [ index ] ]
    bam      = BAM_SORT_STATS_SAMTOOLS.out.bam       // channel: [ val(meta), [ bam ] ]
    bai      = BAM_SORT_STATS_SAMTOOLS.out.bai       // channel: [ val(meta), [ bai ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
