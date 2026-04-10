//
// Screen pathogens for long reads
//

include { MINIMAP2_INDEX                            } from '../../../modules/nf-core/minimap2/index'
include { MINIMAP2_ALIGN                            } from '../../../modules/nf-core/minimap2/align'
include { BAM_SORT_STATS_SAMTOOLS                   } from '../../nf-core/bam_sort_stats_samtools'
include { SAMTOOLS_FAIDX                            } from '../../../modules/nf-core/samtools/faidx'
include { PIGZ_UNCOMPRESS                           } from '../../../modules/nf-core/pigz/uncompress'

workflow MAPPING_LONGREAD {
    take:
    ch_reads_reference // [ [ meta ], [ reads ], [ reference ] ]

    main:
    ch_versions       = channel.empty()
    ch_multiqc_files  = channel.empty()

    // Build the minimap2 index
    ch_reference = ch_reads_reference
        .map { meta, _reads, ref -> [ meta, ref ] }
    MINIMAP2_INDEX ( ch_reference )
    ch_minimap2_index = MINIMAP2_INDEX.out.index

    // Build index fai for the reference
    PIGZ_UNCOMPRESS (
        ch_reads_reference.map { meta, _reads, ref -> [ meta, ref ] }
    )
    ch_ref_uncompressed = PIGZ_UNCOMPRESS.out.file

    SAMTOOLS_FAIDX ( ch_ref_uncompressed, [ [], [] ], false )
    ch_versions = ch_versions.mix( SAMTOOLS_FAIDX.out.versions )

    // Join the uncompressed reference and reference index
    ch_ref_fai = ch_ref_uncompressed
        .join(SAMTOOLS_FAIDX.out.fai, by:0)

    // Join the reads, minimap2 index, reference and reference index
    ch_reads_with_index = ch_reads_reference
        .map { meta, reads, _ref -> [ meta, reads ] }
        .join(ch_minimap2_index, by: 0)
        .join(ch_ref_fai, by:0)
        .multiMap { meta, reads, index, ref, fai ->
            ch_reads: [meta, reads]
            ch_minimap2_index: [meta, index]
            ch_ref: [meta, ref, fai]
        }
    // Align
    MINIMAP2_ALIGN (
        ch_reads_with_index.ch_reads,
        ch_reads_with_index.ch_minimap2_index,
        true,   // bam_format
        'bai',  // bam_index_extension
        false,  // cigar_paf
        false   // cigar_bam
    )

    // Sort and stats
    ch_bam_ref_fai = MINIMAP2_ALIGN.out.bam
        .join( ch_reads_with_index.ch_ref, by: 0 )
        .multiMap { meta, bam, ref, fai ->
            ch_bam: [meta, bam]
            ch_ref_fai: [meta, ref, fai]
        }

    BAM_SORT_STATS_SAMTOOLS ( ch_bam_ref_fai.ch_bam, ch_bam_ref_fai.ch_ref_fai )

    ch_multiqc_files = ch_multiqc_files.mix(BAM_SORT_STATS_SAMTOOLS.out.flagstat.collect{ _meta, flagstat_file -> flagstat_file }.ifEmpty([]))

    emit:
    index    = MINIMAP2_INDEX.out.index              // channel: [ val(meta), [ index ] ]
    bam      = BAM_SORT_STATS_SAMTOOLS.out.bam       // channel: [ val(meta), [ bam ] ]
    bai      = BAM_SORT_STATS_SAMTOOLS.out.index       // channel: [ val(meta), [ bai ] ]
    flagstat = BAM_SORT_STATS_SAMTOOLS.out.flagstat  // channel: [ val(meta), [ flagstat ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
