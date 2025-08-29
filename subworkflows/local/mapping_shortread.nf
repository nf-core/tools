//
// Mapping
//

include { BOWTIE2_BUILD                   } from '../../modules/nf-core/bowtie2/build/main'
include { FASTQ_ALIGN_BOWTIE2             } from '../nf-core/fastq_align_bowtie2/main'

workflow MAPPING_SHORTREAD {
    take:
    reads          // [ [ meta ], [ reads ] ]
    reference      // [ [ meta ], [ reference ] ]

    main:
    ch_versions = Channel.empty()
    ch_multiqc_files = Channel.empty()


    // Build the index
    BOWTIE2_BUILD ( reference )
    ch_versions = ch_versions.mix( BOWTIE2_BUILD.out.versions )

    // Mapping
    FASTQ_ALIGN_BOWTIE2 (
        reads,                          // ch_reads
        BOWTIE2_BUILD.out.index,        // ch_index
        false,                          // save unaligned
        false,                          // sort bam
        reference
    )
    ch_versions = ch_versions.mix ( FASTQ_ALIGN_BOWTIE2.out.versions )
    ch_multiqc_files = ch_multiqc_files.mix ( FASTQ_ALIGN_BOWTIE2.out.stats.collect{it[1]}.ifEmpty([]) )
    ch_multiqc_files = ch_multiqc_files.mix ( FASTQ_ALIGN_BOWTIE2.out.flagstat.collect{it[1]}.ifEmpty([]) )
    ch_multiqc_files = ch_multiqc_files.mix ( FASTQ_ALIGN_BOWTIE2.out.idxstats.collect{it[1]}.ifEmpty([]) )


    emit:
    index    = BOWTIE2_BUILD.out.index               // channel: [ val(meta), [ bam ] ]
    bam      = FASTQ_ALIGN_BOWTIE2.out.bam           // channel: [ val(meta), [ bam ] ]
    bai      = FASTQ_ALIGN_BOWTIE2.out.bai           // channel: [ val(meta), [ bai ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
