//
// BLASTN/BLASTX
//

include { UNTAR  as UNTAR_BLASTN                                } from '../../../modules/nf-core/untar'
include { UNTAR  as UNTAR_BLASTX                                } from '../../../modules/nf-core/untar'
include { BLAST_BLASTN                                          } from '../../../modules/nf-core/blast/blastn'
include { DIAMOND_BLASTX                                        } from '../../../modules/nf-core/diamond/blastx'
include { FILTER_BLAST as FILTER_BLASTN                         } from '../../../modules/local/filter_blast'
include { FILTER_BLAST as FILTER_BLASTX                         } from '../../../modules/local/filter_blast'

workflow BLAST {
    take:
    query           // channel: [ val(meta), path(fasta) ]
    blastn_db       // channel: [ val(meta), path(db) ]
    blastx_db       // channel: [ val(meta), path(db) ]
    blast_header    // channel: [ path(header) ]

    main:
    ch_blast_hits_taxid = channel.empty()

    ch_blastn_filtered = channel.empty()
    ch_blastx_filtered = channel.empty()

    // BLASTN
    if ( !params.skip_blastn ) {
        // Prepare the BLASTN database
        if ( blastn_db.endsWith('.tar.gz') ) {
            UNTAR_BLASTN (
                [ [:], file( blastn_db, checkIfExists: true ) ]
            )
            ch_blastn_db = UNTAR_BLASTN.out.untar
        } else {
            ch_blastn_db = [ [:], file (blastn_db, checkIfExists: true ) ]
        }

        // BLASTN
        BLAST_BLASTN ( query, ch_blastn_db, [], [], [] )

        // Filter BLASTN hits
        ch_blastn_hits = BLAST_BLASTN.out.txt.filter { _meta, blastn_hits -> blastn_hits.size() >0 }
        FILTER_BLASTN ( ch_blastn_hits, file( blast_header, checkIfExists: true ))
        ch_blastn_filtered = ch_blastn_filtered.mix( FILTER_BLASTN.out.filtered_blast )
        // Extract unique taxids from BLASTN hit results
        ch_blastn_hits_taxid = FILTER_BLASTN.out.filtered_blast
            .flatMap { meta, blastn_hits ->
                blastn_hits.splitCsv( sep: '\t', header: true )
                    .collect { row -> [ row.staxid, meta, blastn_hits ] }
            }
            .unique { staxid, meta, _blastn_hits -> [staxid, meta.id, meta.taxid, meta.tool]}
            .map { staxid, meta, _blastn_hits -> [ staxid, meta ] }
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
        } else {
            ch_blastx_db = [ [:], file( blastx_db, checkIfExists: true ) ]
        }

        // Filter out blastx if meta.tools is "diamond"
        ch_query_for_blastx = query.filter { meta, fasta -> meta.tool != 'diamond' }

        // BLASTX:DIAMOND
        DIAMOND_BLASTX (
            ch_query_for_blastx,
            ch_blastx_db,
            'txt',
            'qseqid sseqid slen pident qlen length qcovhsp nident evalue bitscore staxids sscinames'
        )

        // Filter BLASTX hits
        ch_blastx_hits = DIAMOND_BLASTX.out.txt.filter { _meta, blastx_hits -> blastx_hits.size() > 0 }
        FILTER_BLASTX ( ch_blastx_hits, file( blast_header, checkIfExists: true ))
        ch_blastx_filtered = ch_blastx_filtered.mix( FILTER_BLASTX.out.filtered_blast)
        // Extract unique taxids from BLASTX hit results
        ch_blastx_hits_taxid = FILTER_BLASTX.out.filtered_blast
            .flatMap { meta, blastx_hits ->
                blastx_hits.splitCsv( sep: '\t', header: true )
                    .collect { row -> [ row.staxid, meta, blastx_hits ] }
            }
            .unique { staxid, meta, _blastx_hits -> [staxid, meta.id, meta.taxid, meta.tool]}
            .map { staxid, meta, _blastx_hits -> [ staxid, meta ] }
            ch_blast_hits_taxid = ch_blast_hits_taxid.mix ( ch_blastx_hits_taxid )
    }
    // Make blast taxid unique per meta.id, meta_taxid and meta.tool combination
    ch_blast_hits_taxid_uniq = ch_blast_hits_taxid
        .unique { staxid, meta -> [staxid, meta.id, meta.taxid, meta.tool] }

    emit:
    unique_taxid = ch_blast_hits_taxid_uniq // eg: ['211044', ['id':'SRR13439799', 'instrument_platform':'OXFORD_NANOPORE', 'single_end':true, 'taxid':'211044', 'tool':'centrifuge']]
    blastn_filtered = ch_blastn_filtered    // [ meta, filtered_blast ]
    blastx_filtered = ch_blastx_filtered    // [ meta, filtered_blast ]
}
