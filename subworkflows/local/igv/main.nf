//
// IGV visualization
//

include { SAMTOOLS_INDEX      } from '../../../modules/nf-core/samtools/index'
include { SAMTOOLS_FAIDX      } from '../../../modules/nf-core/samtools/faidx'
include { BEDTOOLS_GENOMECOV  } from '../../../modules/nf-core/bedtools/genomecov'
include { PIGZ_UNCOMPRESS     } from '../../../modules/nf-core/pigz/uncompress'
include { IGVREPORTS          } from '../../../modules/nf-core/igvreports'

workflow IGV {
    take:
    ch_bam_bai_reference   // [ [ meta ], [ bam ], [bai], [ref] ]

    main:
    // Extract and index mapped reads
    BEDTOOLS_GENOMECOV (
        ch_bam_bai_reference.map { meta, bam, _bai, _ref -> [ meta, bam, "1" ] },
        [],
        'bed',
        true
    )

    // Uncompress and index the reference genome
    PIGZ_UNCOMPRESS (
        ch_bam_bai_reference.map { meta, _bam, _bai, ref -> [ meta, ref ] }
    )
    ch_ref_uncompressed = PIGZ_UNCOMPRESS.out.file
        .map { meta, ref -> [meta, ref, []]}
    SAMTOOLS_FAIDX ( ch_ref_uncompressed, false )

    // Join all channels together
    ch_bam_bai = ch_bam_bai_reference.map { meta, bam, bai, _ref -> [ meta, bam, bai ] }

    ch_bed_bam_bai = BEDTOOLS_GENOMECOV.out.genomecov
        .join( ch_bam_bai, by: 0 )

    ch_fasta_fai = PIGZ_UNCOMPRESS.out.file
        .join( SAMTOOLS_FAIDX.out.fai, by: 0 )

    ch_igv_input = ch_bed_bam_bai
        .join(ch_fasta_fai, by: 0)

    // IGV reports - use explicit parameter names
    IGVREPORTS (
        ch_igv_input.map { meta, bed, bam, bai, _fasta, _fai ->
            [ meta, bed, bam, bai ]
        },
        ch_igv_input.map { meta, _bed, _bam, _bai, fasta, fai ->
            [ meta, fasta, fai ]
        }
    )

    emit:
    report        = IGVREPORTS.out.report
    fna           = PIGZ_UNCOMPRESS.out.file
    fai           = SAMTOOLS_FAIDX.out.fai
}
