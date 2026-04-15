//
// Fetch genomes with BLAST hits
//

workflow FETCH_BLAST_GENOMES {
    take:
    taxid2genome          // [ path(taxid2genome) ]
    ch_blast_taxid           // [ taxid, meta ]
    ch_reads              // [ meta, reads ]

    main:

    ch_taxid2genome = channel.fromPath ( taxid2genome, checkIfExists: true )
        .splitCsv ( sep:'\t', header: true )
        .map { row ->
            def organism_reformat = row.organism
                .replaceAll(/[^A-Za-z0-9]/, '-') // Replace special chars with dashes
                .replaceAll(/-+/, '-') // Replace multiple dashes with single dash
                .replaceAll(/^-+|-+$/, '')        // Remove leading and trailing dashes
            [ row.taxid, organism_reformat, file( row.genome, checkIfExists: true ) ] }

    // Fetch genomes and reads with BLAST hits
    if ( !params.skip_blastn || !params.skip_blastx ) {
        // Collect all available taxids for checking
        ch_available_taxids = ch_taxid2genome
            .map { taxid, _organism, _genome -> taxid }
            .collect()
            .map { taxid -> taxid.toSet() }  // Stores all taxids in a Set, automatically removing any duplicates.
        // Check for missing taxids and emit warnings
        ch_genomes_blast = ch_blast_taxid
            .combine(ch_available_taxids)
            .map { blast_taxid, meta, available_taxids ->
                if (!available_taxids.contains(blast_taxid)) {
                    log.warn "WARNING: Blast taxid ${blast_taxid} for sample ${meta.id}_${meta.taxid}_${meta.tool} not found in params.taxid2genome - skipping genome fetching!"
                    return null
                }
                return [ blast_taxid, meta ]
            }
            .filter { item -> item != null }
            .combine(ch_taxid2genome)
            .filter { blast_taxid, _meta, genome_taxid, _organism, _genome -> blast_taxid == genome_taxid } // Filter to keep only matching taxids
            .map { blast_taxid, meta, _genome_taxid, organism, genome -> [blast_taxid, meta, organism, genome] }
    } else {
        // Create empty channel if BLAST steps are skipped
        ch_genomes_blast = channel.empty()
    }

    ch_genomes_reads = ch_genomes_blast
        .map { blast_taxid, meta, organism, genome ->
            [ "${meta.id}_${meta.taxid}_${meta.tool}", blast_taxid, meta, organism, genome ]
        }
        .combine(
            ch_reads.map { meta, reads -> [ "${meta.id}_${meta.taxid}_${meta.tool}", meta, reads ]},
            by:0
        )
        .map { _meta_joined, blast_taxid, _meta1, organism, genome, meta2, reads ->
            // Keep a genome-specific key in meta so downstream joins cannot mix references
            def genome_id = genome.name.tokenize('_').take(2).join('_')
            def new_meta = meta2 + [mapping_taxid: blast_taxid, organism: organism, genome_id: genome_id]
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
