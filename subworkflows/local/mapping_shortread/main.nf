//
// Mapping
//

include { BOWTIE2_BUILD                             } from '../../../modules/nf-core/bowtie2/build'
include { FASTQ_ALIGN_BOWTIE2                       } from '../../nf-core/fastq_align_bowtie2'
include { SAMTOOLS_FAIDX                            } from '../../../modules/nf-core/samtools/faidx'
include { PIGZ_UNCOMPRESS                           } from '../../../modules/nf-core/pigz/uncompress'

workflow MAPPING_SHORTREAD {
    take:
    ch_reads_reference // [ [ meta ], [ reads ], [ reference ] ]

    main:
    ch_versions = channel.empty()
    ch_multiqc_files = channel.empty()

    // Build the bowtie2 index
    BOWTIE2_BUILD (
        ch_reads_reference.map { meta, _reads, ref -> [ meta, ref ] }
    )
    ch_bowtie2_index = BOWTIE2_BUILD.out.index

    // Build the reference index fai
    PIGZ_UNCOMPRESS (
        ch_reads_reference.map { meta, _reads, ref -> [ meta, ref ] }
    )
    ch_ref_uncompressed = PIGZ_UNCOMPRESS.out.file
        .map { meta, ref -> [meta, ref, []]}

    SAMTOOLS_FAIDX ( ch_ref_uncompressed, false )

    // Join the uncompressed reference and reference index
    ch_ref_fai = ch_ref_uncompressed
        .map {meta, ref, _empty -> [meta, ref]}
        .join(SAMTOOLS_FAIDX.out.fai, by:0)

    // Join the reads, minimap2 index, reference and reference index
    ch_reads_with_index = ch_reads_reference
        .map { meta, reads, _ref -> [ meta, reads ] }
        .join(ch_bowtie2_index, by: 0)
        .join(ch_ref_fai, by:0)
        .multiMap { meta, reads, bowtie2_index, ref, fai ->
            reads: [meta, reads]
            index: [meta, bowtie2_index]
            fasta_fai: [meta, ref, fai]
        }

    // Mapping
    FASTQ_ALIGN_BOWTIE2 (
        ch_reads_with_index.reads,
        ch_reads_with_index.index,
        false,                          // save unaligned
        false,                          // sort bam
        ch_reads_with_index.fasta_fai
    )

    ch_multiqc_files = ch_multiqc_files.mix ( FASTQ_ALIGN_BOWTIE2.out.flagstat.collect{ _meta, flagstat_file -> flagstat_file }.ifEmpty([]) )

    emit:
    index    = BOWTIE2_BUILD.out.index               // channel: [ val(meta), [ index ] ]
    bam      = FASTQ_ALIGN_BOWTIE2.out.bam           // channel: [ val(meta), [ bam ] ]
    bai      = FASTQ_ALIGN_BOWTIE2.out.index           // channel: [ val(meta), [ bai ] ]
    flagstat = FASTQ_ALIGN_BOWTIE2.out.flagstat      // channel: [ val(meta), [ flagstat ] ]
    versions = ch_versions                           // channel: [ versions.yml ]
    mqc      = ch_multiqc_files
}
