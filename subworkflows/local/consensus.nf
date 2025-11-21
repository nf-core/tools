//
// Consensus calling
//

include { SAMTOOLS_CONSENSUS as SAMTOOLS_CONSENSUS_SHORTREAD    } from '../../modules/nf-core/samtools/consensus/main'
include { SAMTOOLS_CONSENSUS as SAMTOOLS_CONSENSUS_LONGREAD     } from '../../modules/nf-core/samtools/consensus/main'
include { MEDAKA_PARALLEL as MEDAKA                             } from '../../modules/local/medaka_consensus/main'
include { FILTER_CONSENSUS as FILTER_CONSENSUS_SHORTREAD        } from '../../modules/local/filter_consensus'
include { FILTER_CONSENSUS as FILTER_CONSENSUS_LONGREAD         } from '../../modules/local/filter_consensus'

workflow CONSENSUS {
    take:
    bam                 // channel: [ val(meta), path(bam) ]
    reference           // channel: [ path(fasta) ]
    consensus_min_bases // channel: [ val(consensus_min_bases) ]  default: 50bp

    main:
    ch_versions = channel.empty()
    ch_consensus = channel.empty()

    // Separate short read and long read bam files
    ch_bam = bam
        .branch { meta, bam_file ->
            shortreads: meta.instrument_platform != 'OXFORD_NANOPORE'
                return [ meta, bam_file ]
            longreads: meta.instrument_platform == 'OXFORD_NANOPORE'
                return [ meta, bam_file ]
        }

    // Short read consensus
    if ( params.perform_shortread_consensus ) {
        SAMTOOLS_CONSENSUS_SHORTREAD ( ch_bam.shortreads )
        ch_versions = ch_versions.mix( SAMTOOLS_CONSENSUS_SHORTREAD.out.versions )
        // Remove consensus sequences shorter than params.consensus_min_bases (default: 50 bp)
        FILTER_CONSENSUS_SHORTREAD ( SAMTOOLS_CONSENSUS_SHORTREAD.out.fasta, params.consensus_min_bases )
        ch_versions = ch_versions.mix( FILTER_CONSENSUS_SHORTREAD.out.versions )
        ch_consensus = ch_consensus.mix( FILTER_CONSENSUS_SHORTREAD.out.filtered_consensus.ifEmpty([]) )
    }
    // Long read consensus
    if ( params.perform_longread_consensus ) {
        if ( params.longread_consensus_tool == 'medaka' ) {
            input_medaka  = ch_bam.longreads.combine( Channel.value(reference) ).map{ meta_bam, bam, meta_ref, ref -> [ meta_bam, bam, ref ]}
            MEDAKA ( input_medaka )
            ch_consensus_longread = MEDAKA.out.assembly
            ch_versions = ch_versions.mix(MEDAKA.out.versions)
        } else if ( params.longread_consensus_tool == 'samtools' ) {
            SAMTOOLS_CONSENSUS_LONGREAD ( ch_bam.longreads )
            ch_consensus_longread = SAMTOOLS_CONSENSUS_LONGREAD.out.fasta
            ch_versions = ch_versions.mix( SAMTOOLS_CONSENSUS_LONGREAD.out.versions )
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
