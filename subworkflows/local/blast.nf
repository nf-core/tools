//
// BLASTN/BLASTX
//

include { UNTAR  as UNTAR_BLASTN                                } from '../../modules/nf-core/untar/main'
include { UNTAR  as UNTAR_BLASTX                                } from '../../modules/nf-core/untar/main'
include { BLAST_BLASTN                                          } from '../../modules/nf-core/blast/blastn/main'
include { DIAMOND_BLASTX                                        } from '../../modules/nf-core/diamond/blastx/main'
include { FILTER_BLAST as FILTER_BLASTN                         } from '../../modules/local/filter_blast/main'
include { FILTER_BLAST as FILTER_BLASTX                         } from '../../modules/local/filter_blast/main'

workflow BLAST {
    take:
    query           // channel: [ val(meta), path(fasta) ]
    blastn_db       // channel: [ val(meta), path(db) ]
    blastx_db       // channel: [ val(meta), path(db) ]
    blast_header    // channel: [ path(header) ]

    main:
    ch_versions = Channel.empty()
    ch_blast_hits_taxid = Channel.empty()

    ch_blastn_filtered = Channel.empty()
    ch_blastx_filtered = Channel.empty()

    // BLASTN
    if ( !params.skip_blastn ) {
        // Prepare the BLASTN database
        if ( blastn_db.endsWith('.tar.gz') ) {
            UNTAR_BLASTN (
                [ [:], file( blastn_db, checkIfExists: true ) ]
            )
            ch_blastn_db = UNTAR_BLASTN.out.untar
            ch_versions = ch_versions.mix( UNTAR_BLASTN.out.versions )
        } else {
            ch_blastn_db = [ [:], file (blastn_db, checkIfExists: true ) ]
        }

        // BLASTN
        BLAST_BLASTN ( query, ch_blastn_db )
        ch_versions = ch_versions.mix ( BLAST_BLASTN.out.versions.first() )

        // Filter BLASTN hits
        ch_blastn_hits = BLAST_BLASTN.out.txt.filter { meta, blastn_hits -> blastn_hits.size() >0 }
        FILTER_BLASTN ( ch_blastn_hits, file( blast_header, checkIfExists: true ))
        ch_versions = ch_versions.mix( FILTER_BLASTN.out.versions.first() )
        ch_blastn_filtered = ch_blastn_filtered.mix( FILTER_BLASTN.out.filtered_blast )
        // Extract unique taxids from BLASTN hit results
        ch_blastn_hits_taxid = FILTER_BLASTN.out.filtered_blast
            .flatMap { meta, blastn_hits ->
                blastn_hits.splitCsv( sep: '\t', header: true )
                    .collect { row -> [ row.staxid, meta, blastn_hits ] }
            }
            .unique { it[0] }
            .map { taxid, meta, blastn_hits -> [ taxid, meta ] }
        ch_blast_hits_taxid = ch_blast_hits_taxid.mix( ch_blastn_hits_taxid )
    }

    // BLASTX
    if ( !params.skip_blastx ) {
        //Prepare the BLASTX database
        if ( blastx_db.endsWith('.tar.gz') ) {
            UNTAR_BLASTX (
                [ [:],file( blastx_db, checkIfExists: true )]
            )
            ch_blastx_db = UNTAR_BLASTX.out.untar
            ch_versions = ch_versions.mix( UNTAR_BLASTX.out.versions )
        } else {
            ch_blastx_db = [ [:], file( blastx_db, checkIfExists: true ) ]
        }

        // BLASTX:DIAMOND
        DIAMOND_BLASTX (
            query,
            ch_blastx_db,
            'txt',
            'qseqid sseqid slen pident qlen length qcovhsp nident evalue bitscore staxids sscinames'
        )
        ch_versions = ch_versions.mix( DIAMOND_BLASTX.out.versions.first() )

        // Filter BLASTX hits
        ch_blastx_hits = DIAMOND_BLASTX.out.txt.filter { meta, blastx_hits -> blastx_hits.size() > 0 }
        FILTER_BLASTX ( ch_blastx_hits, file( blast_header, checkIfExists: true ))
        ch_versions = ch_versions.mix( FILTER_BLASTX.out.versions.first() )
        ch_blastx_filtered = ch_blastx_filtered.mix( FILTER_BLASTX.out.filtered_blast)
        // Extract unique taxids from BLASTX hit results
        ch_blastx_hits_taxid = FILTER_BLASTX.out.filtered_blast
            .flatMap { meta, blastx_hits ->
                blastx_hits.splitCsv( sep: '\t', header: true )
                    .collect { row -> [ row.staxid, meta, blastx_hits ] }
            }
            .unique { it[0] }  // Remove duplicate taxids
            .map { taxid, meta, blastx_hits -> [ taxid, meta ] }
            ch_blast_hits_taxid = ch_blast_hits_taxid.mix ( ch_blastx_hits_taxid )
    }
    ch_blast_hits_taxid_uniq = ch_blast_hits_taxid.unique()

    emit:
    unique_taxid = ch_blast_hits_taxid_uniq // eg: ['211044', ['id':'SRR13439799', 'instrument_platform':'OXFORD_NANOPORE', 'single_end':true, 'taxid':'211044', 'tool':'centrifuge']]
    blastn_filtered = ch_blastn_filtered    // [ meta, filtered_blast ]
    blastx_filtered = ch_blastx_filtered    // [ meta, filtered_blast ]
    versions = ch_versions
}
