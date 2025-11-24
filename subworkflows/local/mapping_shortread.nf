//
// Mapping
//

include { BOWTIE2_BUILD                   } from '../../modules/nf-core/bowtie2/build/main'
include { FASTQ_ALIGN_BOWTIE2             } from '../nf-core/fastq_align_bowtie2/main'

workflow MAPPING_SHORTREAD {
    take:
    ch_reads_reference // [ [ meta ], [ reads ], [ reference ] ]

    main:
    ch_versions = channel.empty()
    ch_multiqc_files = channel.empty()

    // Build the index
    BOWTIE2_BUILD (
        ch_reads_reference.map { meta, reads, ref -> [ meta, ref ] }
    )
    ch_versions = ch_versions.mix( BOWTIE2_BUILD.out.versions )

    // Join the built index back with the original paired data
    ch_reads_with_index = ch_reads_reference
        .map { meta, reads, ref -> [ meta, reads, ref ] }
        .join(BOWTIE2_BUILD.out.index, by: 0)
        .map { meta, reads, ref, index ->
            [ meta, reads, index, ref ]
        }

    // Mapping
    FASTQ_ALIGN_BOWTIE2 (
        ch_reads_with_index.map { meta, reads, index, ref -> [ meta, reads ] },
        ch_reads_with_index.map { meta, reads, index, ref -> [ meta, index ] },
        false,                          // save unaligned
        false,                          // sort bam
        ch_reads_with_index.map { meta, reads, index, ref -> [ meta, ref ] }
    )
    ch_versions = ch_versions.mix ( FASTQ_ALIGN_BOWTIE2.out.versions )
    ch_multiqc_files = ch_multiqc_files.mix ( FASTQ_ALIGN_BOWTIE2.out.flagstat.collect{it[1]}.ifEmpty([]) )

    emit:
    index    = BOWTIE2_BUILD.out.index               // channel: [ val(meta), [ index ] ]
    bam      = FASTQ_ALIGN_BOWTIE2.out.bam           // channel: [ val(meta), [ bam ] ]
    bai      = FASTQ_ALIGN_BOWTIE2.out.bai           // channel: [ val(meta), [ bai ] ]
    flagstat = FASTQ_ALIGN_BOWTIE2.out.flagstat      // channel: [ val(meta), [ flagstat ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
