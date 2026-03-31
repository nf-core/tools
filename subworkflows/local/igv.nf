//
// IGV visualization
//

include { SAMTOOLS_INDEX      } from '../../modules/nf-core/samtools/index/main'
include { SAMTOOLS_FAIDX      } from '../../modules/nf-core/samtools/faidx/main'
include { BEDTOOLS_GENOMECOV  } from '../../modules/nf-core/bedtools/genomecov/main'
include { PIGZ_UNCOMPRESS     } from '../../modules/nf-core/pigz/uncompress/main'
include { IGVREPORTS          } from '../../modules/nf-core/igvreports/main'

workflow IGV {
    take:
    ch_bam_bai_reference   // [ [ meta ], [ bam ], [bai], [ref] ]

    main:
    ch_versions = channel.empty()

    // Extract and index mapped reads
    BEDTOOLS_GENOMECOV (
        ch_bam_bai_reference.map { meta, bam, bai, ref -> [ meta, bam, "1" ] },
        [],
        'bed',
        true
    )
    ch_versions = ch_versions.mix( BEDTOOLS_GENOMECOV.out.versions )

    // Uncompress and index the reference genome
    PIGZ_UNCOMPRESS (
        ch_bam_bai_reference.map { meta, bam, bai, ref -> [ meta, ref ] }
    )
    ch_versions = ch_versions.mix( PIGZ_UNCOMPRESS.out.versions )

    SAMTOOLS_FAIDX ( PIGZ_UNCOMPRESS.out.file, [ [], [] ], false )
    ch_versions = ch_versions.mix( SAMTOOLS_FAIDX.out.versions )

    // Join all channels together
    ch_bam_bai = ch_bam_bai_reference.map { meta, bam, bai, ref -> [ meta, bam, bai ] }

    ch_bed_bam_bai = BEDTOOLS_GENOMECOV.out.genomecov
        .join( ch_bam_bai, by: 0 )

    ch_fasta_fai = PIGZ_UNCOMPRESS.out.file
        .join( SAMTOOLS_FAIDX.out.fai, by: 0 )

    ch_igv_input = ch_bed_bam_bai
        .join(ch_fasta_fai, by: 0)

    // IGV reports - use explicit parameter names
    IGVREPORTS (
        ch_igv_input.map { meta, bed, bam, bai, fasta, fai ->
            [ meta, bed, bam, bai ]
        },
        ch_igv_input.map { meta, bed, bam, bai, fasta, fai ->
            [ meta, fasta, fai ]
        }
    )
    ch_versions = ch_versions.mix(IGVREPORTS.out.versions)

    emit:
    report        = IGVREPORTS.out.report
    fna           = PIGZ_UNCOMPRESS.out.file
    fai           = SAMTOOLS_FAIDX.out.fai
    versions      = ch_versions
}
