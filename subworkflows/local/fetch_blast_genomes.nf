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
        .map { row -> [ row.taxid, row.organism, file( row.genome, checkIfExists: true ) ] }

    // Fetch genomes and reads with BLAST hits
    if ( !params.skip_blastn || !params.skip_blastx ) {
        // Collect all available taxids for checking
        ch_available_taxids = ch_taxid2genome
            .map { taxid, organism, genome -> taxid }
            .collect()
            .map { it.toSet() }  // Stores all taxids in a Set, automatically removing any duplicates.
        // Check for missing taxids and emit warnings
        ch_genomes_blast = blast_taxid
            .combine(ch_available_taxids)
            .map { blast_taxid, meta, available_taxids ->
                if (!available_taxids.contains(blast_taxid)) {
                    log.warn "WARNING: Taxid ${blast_taxid} not found in params.taxid2genome - skipping genome fetching!"
                    return null
                }
                return [ blast_taxid, meta ]
            }
            .filter { it != null }
            .join(ch_taxid2genome)
    } else {
        // Create empty channel if BLAST steps are skipped
        ch_genomes_blast = Channel.empty()
    }

    ch_genomes_reads = ch_genomes_blast
        .map { blast_taxid, meta, organism, genome ->
            [ "${meta.id}_${meta.taxid}_${meta.tool}", blast_taxid, meta, organism, genome ] }
        .join(
            ch_reads.map { meta, reads -> [ "${meta.id}_${meta.taxid}_${meta.tool}", meta, reads ]},
            by: 0
        )
        .map { meta_joined, blast_taxid, meta1, organism, genome, meta2, reads ->
            def new_meta = meta2.clone()
            new_meta.mapping_taxid = blast_taxid
            new_meta.organism = organism
            [ new_meta, reads, genome ]
        }

    ch_genomes_reads_branched = ch_genomes_reads
        .branch { meta, reads, genome ->
            shortreads: meta.instrument_platform != 'OXFORD_NANOPORE'
                return [ meta, reads, genome ]
            longreads: meta.instrument_platform == 'OXFORD_NANOPORE'
                return [ meta, reads, genome ]
        }

    // Short reads - split into reads and genomes channels
    ch_mapping_shortreads = ch_genomes_reads_branched.shortreads
        .multiMap { meta, reads, genome ->
            reads: [ meta, reads ]
            genome: [ meta, genome ]
        }

    // Long reads - split into reads and genomes channels
    ch_mapping_longreads = ch_genomes_reads_branched.longreads
        .multiMap { meta, reads, genome ->
            reads: [ meta, reads ]
            genome: [ meta, genome ]
        }

    emit:
    shortreads         = ch_mapping_shortreads.reads          // [ meta, reads ]
    longreads          = ch_mapping_longreads.reads           // [ meta, reads ]
    shortreads_genome  = ch_mapping_shortreads.genome         // [ meta, genome ]
    longreads_genome   = ch_mapping_longreads.genome          // [ meta, genome ]
}
