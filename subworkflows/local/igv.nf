//
// IGV visualization
//

include { SAMTOOLS_VIEW       } from '../../modules/nf-core/samtools/view/main'
include { SAMTOOLS_INDEX      } from '../../modules/nf-core/samtools/index/main'
include { SAMTOOLS_FAIDX      } from '../../modules/nf-core/samtools/faidx/main'
include { BEDTOOLS_GENOMECOV  } from '../../modules/nf-core/bedtools/genomecov/main'
include { PIGZ_UNCOMPRESS     } from '../../modules/nf-core/pigz/uncompress/main'
include { IGVREPORTS          } from '../../modules/nf-core/igvreports/main'

workflow IGV {
    take:
    ch_bam_bai_reference   // [ [ meta ], [ bam ], [bai], [ref] ]

    main:
    ch_versions = Channel.empty()

    // Extract and index mapped reads
    BEDTOOLS_GENOMECOV ( ch_bam_bai_reference.map { [it[0], it[1], "1"]}, [], 'bed', true )
    ch_versions = ch_versions.mix( BEDTOOLS_GENOMECOV.out.versions )

    // Uncompress and index the reference genome
    PIGZ_UNCOMPRESS ( ch_bam_bai_reference.map { it -> [ it[0], it[3] ]} )
    SAMTOOLS_FAIDX ( PIGZ_UNCOMPRESS.out.file, [ [],[] ], false )
    ch_versions = ch_versions.mix( PIGZ_UNCOMPRESS.out.versions )
    ch_versions = ch_versions.mix( SAMTOOLS_FAIDX.out.versions )

    // IGV report
    ch_bam_bai = ch_bam_bai_reference.map { meta, bam, bai, ref -> [meta, bam, bai]}
    ch_bed_bam_bai = BEDTOOLS_GENOMECOV.out.genomecov.join( ch_bam_bai )
    ch_fasta_fai = PIGZ_UNCOMPRESS.out.file.join( SAMTOOLS_FAIDX.out.fai )

    IGVREPORTS ( ch_bed_bam_bai, ch_fasta_fai )
    ch_versions = ch_versions.mix(IGVREPORTS.out.versions)

    emit:
    report        = IGVREPORTS.out.report
    fna           = PIGZ_UNCOMPRESS.out.file
    fai           = SAMTOOLS_FAIDX.out.fai
    versions      = ch_versions

}
