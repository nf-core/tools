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
    bam            // [ [ meta ], [ bam ] ]
    bai            // [ [ meta ], [ bai ] ]
    reference     // [ [ meta ], [ reference ] ]

    main:
    ch_versions = Channel.empty()

    // Extract and index mapped reads
    SAMTOOLS_VIEW ( bam.join( bai ), [ [],[] ], [], 'bai' )
    ch_versions = ch_versions.mix( SAMTOOLS_VIEW.out.versions )
    SAMTOOLS_INDEX ( SAMTOOLS_VIEW.out.bam )
    ch_versions = ch_versions.mix( SAMTOOLS_INDEX.out.versions )

    // Create a bed file
    ch_bedtools_input = SAMTOOLS_VIEW.out.bam.join( SAMTOOLS_INDEX.out.bai )
    BEDTOOLS_GENOMECOV ( ch_bedtools_input.map { [it[0], it[1], "1"]}, [], 'bed', true )
    ch_versions = ch_versions.mix( BEDTOOLS_GENOMECOV.out.versions )

    // Uncompress and index the reference genome
    PIGZ_UNCOMPRESS ( reference )
    SAMTOOLS_FAIDX ( PIGZ_UNCOMPRESS.out.file, [ [],[] ], false )
    ch_versions = ch_versions.mix( PIGZ_UNCOMPRESS.out.versions )
    ch_versions = ch_versions.mix( SAMTOOLS_FAIDX.out.versions )

    // IGV report
    ch_bam_bai = SAMTOOLS_VIEW.out.bam.join( SAMTOOLS_INDEX.out.bai )
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
