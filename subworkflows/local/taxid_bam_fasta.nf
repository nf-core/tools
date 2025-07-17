//
// Prepare an individual BAM/FASTA file for each pathogen with mapped reads
//

include { SUBSET_BAM as SUBSET_BAM_PASS                     } from '../../modules/local/subset_bam'
include { SUBSET_BAM as SUBSET_BAM_FAIL                     } from '../../modules/local/subset_bam'
include { SAMTOOLS_SORT as SAMTOOLS_SORT_PASS               } from '../../modules/nf-core/samtools/sort/main'
include { SAMTOOLS_SORT as SAMTOOLS_SORT_FAIL               } from '../../modules/nf-core/samtools/sort/main'
include { SAMTOOLS_INDEX                                    } from '../../modules/nf-core/samtools/index/main'
include { SAMTOOLS_IDXSTATS                                 } from '../../modules/nf-core/samtools/idxstats/main'
include { SAMTOOLS_FASTA                                    } from '../../modules/nf-core/samtools/fasta/main'

workflow TAXID_BAM_FASTA {
    take:
    bam               // Channel: [ val(meta), path(bam) ]
    bai               // Channel: [ val(meta), path(bai) ]
    accession2taxid   // Channel: path(accession2taxid)
    min_read_counts   // Value: minimum number of reads to keep a BAM file

    main:
    ch_versions       = Channel.empty()
    ch_multiqc_files  = Channel.empty()

    // Combine BAM and BAI files
    input_bam = bam.join(bai, by: 0)
    // Get idxstats for input BAM
    SAMTOOLS_IDXSTATS(input_bam)
    ch_accession = SAMTOOLS_IDXSTATS.out.idxstats
        .map { it[1] }
        .splitCsv(header: false, sep: "\t")
        .filter { it -> it[0] != "*" }  // Remove the last row

    ch_versions.mix(SAMTOOLS_IDXSTATS.out.versions.first())

    // Load accession2taxid map
    ch_accession2taxidmap = accession2taxid.splitCsv(header: false, sep: "\t")

    // Join accessions with taxids and group by taxid
    ch_accession_taxid = ch_accession2taxidmap
        .join(ch_accession)
        .map { it ->
            def num_reads = it[3].toInteger()
            [it[0], it[1], num_reads]
        }
        .filter { accessions, taxid, num_reads -> num_reads > 0 }
        .groupTuple(by: 1)
        .map { accession_list, taxid, num_reads ->
            def total_reads = num_reads.sum()
            [accession_list, taxid, total_reads]
        }
        .branch {
            pass: it[2] >= min_read_counts // The number of mapped reads to a taxID greater than params.min_read_counts
                return [it[0], it[1]]
            fail: it[2] < min_read_counts  // The number of mapped reads to a taxID smaller than params.min_read_counts
                return [it[0], it[1]]
        }

    // Prepare individual BAM files for each taxID with the number of mapped reads greater than params.min_read_counts
    ch_consensus_input = ch_accession_taxid.pass
        .combine(input_bam)
        .map { accession_list, taxid, meta, bam, bam_index ->
            def new_meta = meta.clone()
            new_meta.taxid = taxid
            return [new_meta, bam, bam_index, accession_list]
        }
        .multiMap {
            meta, bam, bam_index, accession_list ->
                bam: [meta, bam, bam_index]
                accession: accession_list.flatten()
        }

    // BAM files will be used to call consensus sequences
    SUBSET_BAM_PASS(ch_consensus_input.bam, ch_consensus_input.accession)
    ch_versions = ch_versions.mix(SUBSET_BAM_PASS.out.versions.first())
    SAMTOOLS_SORT_PASS(SUBSET_BAM_PASS.out.bam, [[],[]])
    ch_versions = ch_versions.mix(SAMTOOLS_SORT_PASS.out.versions.first())
    SAMTOOLS_INDEX(SAMTOOLS_SORT_PASS.out.bam)
    ch_versions = ch_versions.mix(SAMTOOLS_INDEX.out.versions.first())

    // Prepare individual FASTA files for each taxID with the number of mapped reads less than params.min_read_counts
    ch_blast_input = ch_accession_taxid.fail
        .combine(input_bam)
        .map { accession_list, taxid, meta, bam, bam_index ->
            def new_meta = meta.clone()
            new_meta.taxid = taxid
            return [new_meta, bam, bam_index, accession_list]
        }
        .multiMap {
            meta, bam, bam_index, accession_list ->
                bam: [meta, bam, bam_index]
                accession: accession_list.flatten()
        }

    // FASTA files will be used as BLAST input
    SUBSET_BAM_FAIL(ch_blast_input.bam, ch_blast_input.accession)
    ch_versions = ch_versions.mix(SUBSET_BAM_FAIL.out.versions.first())
    SAMTOOLS_SORT_FAIL(SUBSET_BAM_FAIL.out.bam, [[],[]])
    ch_versions = ch_versions.mix(SAMTOOLS_SORT_FAIL.out.versions.first())

    SAMTOOLS_FASTA(SAMTOOLS_SORT_FAIL.out.bam, false)
    ch_versions = ch_versions.mix(SAMTOOLS_FASTA.out.versions.first())

    emit:
    versions        = ch_versions
    taxid_bam       = SAMTOOLS_SORT_PASS.out.bam
    taxid_bai       = SAMTOOLS_INDEX.out.bai
    taxid_fasta     = SAMTOOLS_FASTA.out.fasta
}
