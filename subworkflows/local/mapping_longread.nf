//
// Screen pathogens for long reads
//

include { MINIMAP2_INDEX             } from '../../modules/nf-core/minimap2/index/main'
include { MINIMAP2_ALIGN             } from '../../modules/nf-core/minimap2/align/main'
include { BAM_SORT_STATS_SAMTOOLS    } from '../nf-core/bam_sort_stats_samtools/main'
include { SAMTOOLS_FAIDX             } from '../../modules/nf-core/samtools/faidx/main'
include { PIGZ_UNCOMPRESS            } from '../../modules/nf-core/pigz/uncompress/main'

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
    ch_index = MINIMAP2_INDEX.out.index
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
        .join(ch_index, by: 0)
        .join(ch_ref_fai, by:0)

    // Align
    MINIMAP2_ALIGN (
        ch_reads_with_index.map { meta, reads, index, ref, fai -> [ meta, reads ] },
        ch_reads_with_index.map { meta, reads, index, ref, fai -> [ meta, index ] },
        true,   // bam_format
        'bai',  // bam_index_extension
        false,  // cigar_paf
        false   // cigar_bam
    )
    ch_versions = ch_versions.mix( MINIMAP2_ALIGN.out.versions.first() )

    // Sort and stats
    ch_bam_ref_fai = MINIMAP2_ALIGN.out.bam
        .join(
            ch_reads_with_index.map { meta, reads, index, ref, fai -> [ meta, ref, fai ] },
            by: 0
        )
    ch_bam = ch_bam_ref_fai
        .map { meta, bam, ref, fai -> [ meta, bam ] }
    ch_ref_fai = ch_bam_ref_fai
        .map { meta, bam, ref, fai -> [ meta, ref, fai ] }

    BAM_SORT_STATS_SAMTOOLS (
        ch_bam,
        ch_ref_fai
    )

    ch_multiqc_files = ch_multiqc_files.mix(BAM_SORT_STATS_SAMTOOLS.out.flagstat.collect{it[1]}.ifEmpty([]))

    emit:
    index    = MINIMAP2_INDEX.out.index              // channel: [ val(meta), [ index ] ]
    bam      = BAM_SORT_STATS_SAMTOOLS.out.bam       // channel: [ val(meta), [ bam ] ]
    bai      = BAM_SORT_STATS_SAMTOOLS.out.index       // channel: [ val(meta), [ bai ] ]
    flagstat = BAM_SORT_STATS_SAMTOOLS.out.flagstat  // channel: [ val(meta), [ flagstat ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
