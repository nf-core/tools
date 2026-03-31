//
// Prepare an individual BAM/FASTA file for each pathogen with mapped reads
//

include { SUBSET_BAM as SUBSET_BAM_PASS                     } from '../../modules/local/subset_bam'
include { SUBSET_BAM as SUBSET_BAM_FAIL                     } from '../../modules/local/subset_bam'
include { SAMTOOLS_SORT as SAMTOOLS_SORT_PASS               } from '../../modules/nf-core/samtools/sort/main'
include { SAMTOOLS_SORT as SAMTOOLS_SORT_FAIL               } from '../../modules/nf-core/samtools/sort/main'
include { SAMTOOLS_INDEX as  SAMTOOLS_INDEX_PASS            } from '../../modules/nf-core/samtools/index/main'
include { SAMTOOLS_INDEX as  SAMTOOLS_INDEX_FAIL            } from '../../modules/nf-core/samtools/index/main'
include { SAMTOOLS_IDXSTATS                                 } from '../../modules/nf-core/samtools/idxstats/main'
include { SAMTOOLS_FASTA                                    } from '../../modules/nf-core/samtools/fasta/main'
include { SAMTOOLS_FLAGSTAT                                 } from '../../modules/nf-core/samtools/flagstat/main'
include { getFlagstatMappedReads                            } from '../../subworkflows/local/utils_nfcore_metaval_pipeline'

workflow TAXID_BAM_FASTA {
    take:
    bam               // Channel: [ val(meta), path(bam) ]
    bai               // Channel: [ val(meta), path(bai) ]
    accession2taxid   // Channel: path(accession2taxid)
    min_read_counts   // Value: minimum number of reads to keep a BAM file

    main:
    ch_versions        = channel.empty()
    ch_multiqc_files   = channel.empty()
    ch_taxid_bam       = channel.empty()
    ch_taxid_bai       = channel.empty()
    ch_consensus_input = channel.empty()
    ch_blast_input     = channel.empty()

    // Combine BAM and BAI files
    input_bam = bam.join( bai, by: 0 )
    // Get idxstats for input BAM
    SAMTOOLS_IDXSTATS( input_bam )
    // Extract accessions with mapped reads
    ch_accession_with_meta = SAMTOOLS_IDXSTATS.out.idxstats
        .flatMap { meta, idxstats ->
            idxstats.splitCsv( header: false, sep: "\t" )
                // The SAMTOOLS_IDXSTATS.out.idxstats file contains four columns: <reference_name> <reference_length> <mapped_reads> <unmapped_reads>
                // The last row is "* 0 0 0" and should be filtered out, along with rows that have zero mapped reads.
                .findAll { it[0] != "*" && it[2].toInteger() > 0 }
                .collect{ [meta, it[0], it[2].toInteger()] }
        }

    // Load accession2taxid map
    ch_accession2taxidmap = accession2taxid.splitCsv( header: false, sep: "\t" )

    // Join accessions with taxids: [meta, accession, num_reads] + [accession, taxid, organism]
    ch_accession_taxid_with_meta = ch_accession_with_meta
        .combine(ch_accession2taxidmap)
        .filter { meta, accession, num_reads, ref_accession, taxid, organism ->
            accession == ref_accession
        }
        .map { meta, accession, num_reads, ref_accession, taxid, organism ->
            [meta, accession, taxid, organism, num_reads]
        }
        .groupTuple( by: [0, 2, 3] ) // Group by [meta, taxid, organism]
        .map { meta, accession_list, taxid, organism, num_reads_list ->
            [meta, accession_list, taxid, organism, num_reads_list.sum()]
        }
        .branch {
            pass: it[4] >= min_read_counts // The number of mapped reads to a taxID greater than params.min_read_counts
                return [it[0], it[1], it[2], it[3]] // [meta, accession_list, taxid, organism]
            fail: it[4] < min_read_counts  // The number of mapped reads to a taxID smaller than params.min_read_counts
                return [it[0], it[1], it[2], it[3]] // [meta, accession_list, taxid, organism]
        }

    // Prepare individual BAM files for each taxID with the number of mapped reads greater than params.min_read_counts
    ch_consensus_input = ch_accession_taxid_with_meta.pass
        .join( input_bam, by: 0 ) // Join by meta (index 0)
        .map { meta, accession_list, taxid, organism, bam, bam_index ->
            // Create new meta with taxid and organism information
            def new_meta = meta + [taxid: taxid, organism: organism]
            return [ new_meta, bam, bam_index, accession_list ]
        }
        .multiMap {
            meta, bam, bam_index, accession_list ->
                bam: [ meta, bam, bam_index ]
                accession: accession_list.flatten()
        }

    // BAM files will be used to call consensus sequences
    SUBSET_BAM_PASS( ch_consensus_input.bam, ch_consensus_input.accession )
    ch_versions = ch_versions.mix( SUBSET_BAM_PASS.out.versions.first() )
    SAMTOOLS_SORT_PASS( SUBSET_BAM_PASS.out.bam, [[],[],[]], 'bai' )
    SAMTOOLS_INDEX_PASS( SAMTOOLS_SORT_PASS.out.bam )

    // samtools flagstat check if there are any reads mapped to the genome
    SAMTOOLS_FLAGSTAT (SAMTOOLS_SORT_PASS.out.bam.join(SAMTOOLS_INDEX_PASS.out.index))

    ch_mapped_reads = SAMTOOLS_FLAGSTAT.out.flagstat
        .map { meta, flagstat -> [meta] + getFlagstatMappedReads(flagstat)}

    ch_taxid_bam = ch_taxid_bam.mix(SAMTOOLS_SORT_PASS.out.bam)
        .join (ch_mapped_reads, by: [0])
        .filter { meta, bam, mapped, pass -> pass }
        .map { meta, bam, mapped, pass -> [meta, bam] }
    ch_taxid_bai = ch_taxid_bai.mix(SAMTOOLS_INDEX_PASS.out.index)
        .join(ch_mapped_reads, by:[0])
        .filter { meta, bai, mapped, pass -> pass }
        .map { meta, bai, mapped, pass -> [meta, bai] }

    // Prepare individual FASTA files for each taxID with the number of mapped reads less than params.min_read_counts
    ch_blast_input = ch_accession_taxid_with_meta.fail
        .join( input_bam, by: 0 ) // Join by meta (index 0)
        .map { meta, accession_list, taxid, organism, bam, bam_index ->
            // Create new meta with taxid and organism information
            def new_meta = meta + [taxid: taxid, organism: organism]
            return [ new_meta, bam, bam_index, accession_list ]
        }
        .multiMap {
            meta, bam, bam_index, accession_list ->
                bam: [ meta, bam, bam_index ]
                accession: accession_list.flatten()
        }

    // FASTA files will be used as BLAST input, bam file will be used in IGV
    SUBSET_BAM_FAIL(ch_blast_input.bam, ch_blast_input.accession)
    ch_versions = ch_versions.mix(SUBSET_BAM_FAIL.out.versions.first())
    SAMTOOLS_SORT_FAIL(SUBSET_BAM_FAIL.out.bam, [[],[],[]], 'bai')
    SAMTOOLS_INDEX_FAIL(SAMTOOLS_SORT_FAIL.out.bam)

    SAMTOOLS_FASTA(SAMTOOLS_SORT_FAIL.out.bam, false)

    emit:
    versions        = ch_versions
    taxid_bam       = ch_taxid_bam
    taxid_bai       = ch_taxid_bai
    taxid_fasta     = SAMTOOLS_FASTA.out.fasta
    taxid_bam_fail  = SAMTOOLS_SORT_FAIL.out.bam
    taxid_bai_fail  = SAMTOOLS_INDEX_FAIL.out.index
}
