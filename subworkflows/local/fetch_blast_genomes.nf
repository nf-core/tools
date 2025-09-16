//
// Fetch genomes with BLAST hits
//

workflow FETCH_BLAST_GENOMES {
    take:
    taxid2genome          // [ path(taxid2genome) ]
    blast_taxid           // [ taxid, meta ]
    ch_reads              // [ meta, reads ]

    main:

    ch_taxid2genome = Channel.fromPath ( taxid2genome, checkIfExists: true )
        .splitCsv ( sep:'\t', header: true )
        .map { row -> [ row.taxid, file( row.genome, checkIfExists: true ) ] }
    // Fetch genomes and reads with BLAST hits
    if ( !params.skip_blastn || !params.skip_blastx ) {
        ch_genomes_blast = blast_taxid.join ( ch_taxid2genome, failOnMismatch: false )
            .filter { blast_taxid, meta, genome ->
                if ( genome == null ) {
                    log.warn "WARNING: Taxid ${taxid} not found in params.taxid2genome - skipping genome fetching!"
                    return false
                }
                return true
            }
        ch_genomes_reads = ch_genomes_blast
            .map { blast_taxid, meta, genome -> [ "${meta.id}_${meta.taxid}_${meta.tool}", blast_taxid, meta, genome ] }
            .join ( ch_reads.map { meta, reads -> [ "${meta.id}_${meta.taxid}_${meta.tool}", meta, reads ]}, by: 0 )
            .map { meta_joined, blast_taxid, meta1, genome, meta2, reads -> [ blast_taxid, meta2, reads, genome ] }
    }
    // Skip BLAST — Fetch genomes based on taxids predicted by classifiers
    if ( params.skip_blastn && params.skip_blastx ) {
        ch_genomes_reads = ch_reads
            .map { meta, reads -> [ meta.taxid, meta, reads ] }
            .join( ch_taxid2genome, by:0 )
            .map { taxid, meta, reads, genome -> [ taxid, meta, reads, genome ]}
    }

    ch_genomes_reads_branched = ch_genomes_reads
        .branch { taxid, meta, reads, genome ->
            shortreads: meta.instrument_platform != 'OXFORD_NANOPORE'
                return [ taxid, meta, reads, genome ]
            longreads: meta.instrument_platform == 'OXFORD_NANOPORE'
                return [ taxid, meta, reads, genome ]
        }

    // Short reads - combine both mapping operations
    ch_mapping_shortreads = ch_genomes_reads_branched.shortreads
        .multiMap { taxid, meta, reads, genome ->
            reads: [ meta, reads ]
            genome: [ [ id: taxid ], genome ]
        }

    // Long reads - combine both mapping operations
    ch_mapping_longreads = ch_genomes_reads_branched.longreads
        .multiMap { taxid, meta, reads, genome ->
            reads: [ meta, reads ]
            genome: [ [ id: taxid ], genome ]
        }

    emit:
    shortreads         = ch_mapping_shortreads.reads          // [ meta, reads ]
    longreads          = ch_mapping_longreads.reads           // [ meta, reads ]
    shortreads_genome  = ch_mapping_shortreads.genome         // [ meta, genome ]
    longreads_genome   = ch_mapping_longreads.genome          // [ meta, genome ]
}
