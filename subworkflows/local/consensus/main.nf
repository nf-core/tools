//
// Consensus calling
//

include { SAMTOOLS_CONSENSUS as SAMTOOLS_CONSENSUS_SHORTREAD    } from '../../../modules/nf-core/samtools/consensus'
include { SAMTOOLS_CONSENSUS as SAMTOOLS_CONSENSUS_LONGREAD     } from '../../../modules/nf-core/samtools/consensus'
include { MEDAKA_PARALLEL as MEDAKA                             } from '../../../modules/local/medaka_consensus'
include { FILTER_CONSENSUS as FILTER_CONSENSUS_SHORTREAD        } from '../../../modules/local/filter_consensus'
include { FILTER_CONSENSUS as FILTER_CONSENSUS_LONGREAD         } from '../../../modules/local/filter_consensus'

workflow CONSENSUS {
    take:
    ch_bam_bai                 // channel: [ val(meta), path(bam), path(bai) ]
    ch_reference           // channel: [ path(fasta) ]
    consensus_min_bases // channel: [ val(consensus_min_bases) ]  default: 50bp

    main:
    ch_versions = channel.empty()
    ch_consensus = channel.empty()

    // Separate short read and long read bam files
    ch_bam_bai_consensus = ch_bam_bai
        .branch { meta, bam, bai ->
            shortreads: meta.instrument_platform != 'OXFORD_NANOPORE'
                return [ meta, bam, bai ]
            longreads: meta.instrument_platform == 'OXFORD_NANOPORE'
                return [ meta, bam, bai ]
        }

    // Short read consensus
    if ( params.perform_shortread_consensus ) {
        SAMTOOLS_CONSENSUS_SHORTREAD ( ch_bam_bai_consensus.shortreads )
        // Remove consensus sequences shorter than params.consensus_min_bases (default: 50 bp)
        FILTER_CONSENSUS_SHORTREAD ( SAMTOOLS_CONSENSUS_SHORTREAD.out.fasta, params.consensus_min_bases )
        ch_versions = ch_versions.mix( FILTER_CONSENSUS_SHORTREAD.out.versions )
        ch_consensus = ch_consensus.mix( FILTER_CONSENSUS_SHORTREAD.out.filtered_consensus.ifEmpty([]) )
    }
    // Long read consensus
    if ( params.perform_longread_consensus ) {
        if ( params.longread_consensus_tool == 'medaka' ) {
            input_medaka  = ch_bam_bai_consensus.longreads.combine( channel.value(ch_reference) ).map{ meta_bam, bam, _bai, _meta_ref, ref -> [ meta_bam, bam, ref ]}
            MEDAKA ( input_medaka )
            ch_consensus_longread = MEDAKA.out.assembly
            ch_versions = ch_versions.mix(MEDAKA.out.versions)
        } else if ( params.longread_consensus_tool == 'samtools' ) {
            SAMTOOLS_CONSENSUS_LONGREAD ( ch_bam_bai_consensus.longreads )
            ch_consensus_longread = SAMTOOLS_CONSENSUS_LONGREAD.out.fasta
        }
        // Remove consensus sequences shorter than params.consensus_min_bases (default: 50 bp)
        FILTER_CONSENSUS_LONGREAD ( ch_consensus_longread, consensus_min_bases )
        ch_versions = ch_versions.mix( FILTER_CONSENSUS_LONGREAD.out.versions )
        ch_consensus = ch_consensus.mix( FILTER_CONSENSUS_LONGREAD.out.filtered_consensus.ifEmpty([]) )
    }

    emit:
    consensus = ch_consensus // channel: [ val(meta), path(consensus) ]
    versions  = ch_versions   // channel: [ versions.yml ]
}
