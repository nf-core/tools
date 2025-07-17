//
// Consensus calling for long reads
//

include { SAMTOOLS_CONSENSUS        } from '../../modules/nf-core/samtools/consensus/main'
include { MEDAKA_PARALLEL as MEDAKA } from '../../modules/local/medaka_consensus/main'

workflow LONGREAD_CONSENSUS {
    take:
    bam         // channel: [ val(meta), path(bam) ]
    reference   // path(fasta)

    main:
    ch_versions = Channel.empty()

    if ( params.longread_consensus_tool == 'medaka' ) {
        input_medaka  = bam.combine(Channel.value(reference)).map{ meta_bam, bam, meta_ref, ref -> [ meta_bam, bam, ref ]}
        MEDAKA ( input_medaka )
        ch_consensus = MEDAKA.out.assembly
        ch_versions = ch_versions.mix(MEDAKA.out.versions)

    } else if ( params.longread_consensus_tool == 'samtools' ) {
        SAMTOOLS_CONSENSUS ( bam )
        ch_consensus = SAMTOOLS_CONSENSUS.out.fasta
        ch_versions = ch_versions.mix(SAMTOOLS_CONSENSUS.out.versions)
    }

    emit:
    consensus = ch_consensus // channel: [ val(meta), path(consensus) ]
    versions = ch_versions   // channel: [ versions.yml ]
}
