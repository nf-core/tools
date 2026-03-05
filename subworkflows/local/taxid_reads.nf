//
// EXTRACT READS
//

include { EXTRACT_VIRAL_TAXID as KRAKEN2_VIRAL_TAXID      } from '../../modules/local/extract_viral_taxid/main'
include { EXTRACT_VIRAL_TAXID as CENTRIFUGE_VIRAL_TAXID   } from '../../modules/local/extract_viral_taxid/main'
include { EXTRACT_VIRAL_TAXID as DIAMOND_VIRAL_TAXID      } from '../../modules/local/extract_viral_taxid/main'
include { KRAKENTOOLS_EXTRACTKRAKENREADS                  } from '../../modules/nf-core/krakentools/extractkrakenreads/main'
include { EXTRACTCENTRIFUGEREADS                          } from '../../modules/local/extractcentrifugereads/main'
include { EXTRACTDIAMONDREADS                            } from '../../modules/local/extractdiamondreads/main'

workflow TAXID_READS {
    params.taxid

    take:
    reads                   // channel:   [mandatory] [ meta, reads ]
    kraken2_taxpasta        // channel:   [mandatory] [ meta, kraken2_taxpasta ]
    kraken2_result          // channel:   [mandatory] [ meta, kraken2_result ]
    kraken2_report          // channel:   [mandatory] [ meta, kraken2_report ]
    centrifuge_taxpasta     // channel:   [mandatory] [ meta, centrifuge_taxpasta ]
    centrifuge_result       // channel:   [mandatory] [ meta, centrifuge_result ]
    centrifuge_report       // channel:   [mandatory] [ meta, centrifuge_report ]
    diamond_taxpasta        // channel:   [mandatory] [ meta, diamond_taxpasta ]
    diamond_tsv             // channel:   [mandatory] [ meta, diamond_tsv ]


    main:
    ch_versions      = channel.empty()
    ch_taxid_reads   = channel.empty()

    // extract kraken2 reads
    if ( params.extract_kraken2_reads ) {
        if ( params.taxid ) {
            kraken2_params_taxid = kraken2_report.map { meta, kraken2_report -> [ meta.subMap(meta.keySet() - 'tool'), kraken2_report ] }
                .join( kraken2_result, by: 0 )
                .join( reads, by: 0)
                .combine ( Channel.of( params.taxid.split(" ") ) )
                .multiMap { meta, kraken2_report, kraken2_result, reads, taxid  ->
                    taxid: taxid
                    kraken2_result: [ meta + [taxid: taxid], kraken2_result ]
                    reads: [ meta + [taxid: taxid], reads ]
                    kraken2_report: [ meta + [taxid: taxid], kraken2_report ]
                    }

            KRAKENTOOLS_EXTRACTKRAKENREADS(
                kraken2_params_taxid.taxid,
                kraken2_params_taxid.kraken2_result,
                kraken2_params_taxid.reads,
                kraken2_params_taxid.kraken2_report
            )
            ch_taxid_reads_kraken2  = KRAKENTOOLS_EXTRACTKRAKENREADS.out.extracted_kraken2_reads
                .map {meta,reads -> [ meta + [tool:"kraken2"], reads ]}
            ch_versions             = ch_versions.mix( KRAKENTOOLS_EXTRACTKRAKENREADS.out.versions.first() )
        } else {
            kraken2_output = kraken2_taxpasta.join(kraken2_report)
            KRAKEN2_VIRAL_TAXID( [], kraken2_output)

            kraken2_taxids = KRAKEN2_VIRAL_TAXID.out.viral_taxid
                .map { meta, taxid -> [ meta.subMap( meta.keySet() - 'tool' ), taxid ] }
                .splitText()

            kraken2_combined_input = kraken2_result
                .join( reads, by:0)
                .join( kraken2_report.map { meta, kraken2_report -> [ meta.subMap(meta.keySet() - 'tool'), kraken2_report ]}, by:0 )
                .combine( kraken2_taxids, by:0 )
                .multiMap { meta, kraken2_result, reads, kraken2_report, taxid ->
                    taxid: taxid.trim()
                    kraken2_result: [ meta + [ taxid: taxid.trim() ], kraken2_result ]
                    reads: [ meta + [ taxid: taxid.trim() ], reads ]
                    kraken2_report: [ meta + [ taxid: taxid.trim() ], kraken2_report ]
                }

                KRAKENTOOLS_EXTRACTKRAKENREADS(
                kraken2_combined_input.taxid,
                kraken2_combined_input.kraken2_result,
                kraken2_combined_input.reads,
                kraken2_combined_input.kraken2_report
            )
            ch_taxid_reads_kraken2  = KRAKENTOOLS_EXTRACTKRAKENREADS.out.extracted_kraken2_reads
                .map {meta,reads -> [ meta+[tool: "kraken2"]+ [taxid: meta.taxid], reads ]}
        }
        ch_taxid_reads              = ch_taxid_reads.mix(ch_taxid_reads_kraken2)
    }

    // extract centrifuge reads
    if ( params.extract_centrifuge_reads ) {
        if ( params.taxid ) {
            centrifuge_params_taxid = centrifuge_result
                .join( reads, by: 0 )
                .combine( Channel.of( params.taxid.split(" ") ) )
                .multiMap { meta, centrifuge_result, reads, taxid ->
                    taxid: taxid
                    centrifuge_result: [ meta + [taxid: taxid], centrifuge_result, reads ]
                    }

            EXTRACTCENTRIFUGEREADS(
                centrifuge_params_taxid.taxid,
                centrifuge_params_taxid.centrifuge_result
            )
            ch_taxid_reads_centrifuge  = EXTRACTCENTRIFUGEREADS.out.extracted_centrifuge_reads
                .map {meta,reads -> [ meta+[tool:"centrifuge"], reads ]}
            ch_versions                = ch_versions.mix( EXTRACTCENTRIFUGEREADS.out.versions )

            // Remove empty fastq files produced by extracting reads for user defined taxIDs
            EXTRACTCENTRIFUGEREADS.out.extracted_centrifuge_reads
                .collect()
                .map { it -> file("${params.outdir}/extracted_reads/centrifuge") }
                .set { ch_centrifuge_output_dir }
        } else {
            centrifuge_output = centrifuge_taxpasta.join(centrifuge_report)
            CENTRIFUGE_VIRAL_TAXID( [], centrifuge_output )
            centrifuge_taxids = CENTRIFUGE_VIRAL_TAXID.out.viral_taxid
                .map { meta, taxid -> [ meta.subMap( meta.keySet() - 'tool' ), taxid ] }
                .splitText()

            centrifuge_combined_input = centrifuge_result
                .join( reads, by:0 )
                .combine( centrifuge_taxids, by:0 )
                .multiMap { meta, centrifuge_result, reads, taxid ->
                    taxid: taxid.trim()
                    centrifuge_result: [ meta + [ taxid: taxid.trim() ], centrifuge_result, reads ]
                }

            EXTRACTCENTRIFUGEREADS(
                centrifuge_combined_input.taxid,
                centrifuge_combined_input.centrifuge_result
            )
            ch_taxid_reads_centrifuge  = EXTRACTCENTRIFUGEREADS.out.extracted_centrifuge_reads
                .map {meta,reads -> [ meta+[tool:"centrifuge"], reads ]}
        }
        ch_taxid_reads             = ch_taxid_reads.mix(ch_taxid_reads_centrifuge)
    }

    // extract diamond reads
    if ( params.extract_diamond_reads ) {
        if ( params.taxid ) {
            diamond_params_taxid = diamond_tsv.map { meta, diamond_tsv -> [meta.subMap( meta.keySet() - 'tool' ), diamond_tsv ] }
                .join( reads, by:0)
                .combine( Channel.of( params.taxid.split(" ") ))
                .multiMap { meta, diamond_tsv, reads, taxid ->
                    taxid: taxid
                    diamond_tsv: [ meta + [ taxid: taxid ], diamond_tsv, reads ]
                    }

            EXTRACTDIAMONDREADS(
                diamond_params_taxid.taxid,
                params.evalue_threshold,
                diamond_params_taxid.diamond_tsv
            )
            ch_taxid_reads_diamond = EXTRACTDIAMONDREADS.out.extracted_diamond_reads
                .map {meta,reads -> [ meta+[tool:"diamond"], reads ]}
            ch_versions            = ch_versions.mix( EXTRACTDIAMONDREADS.out.versions )

            // Remove empty fastq files produced by extracting reads for user defined taxIDs
            EXTRACTDIAMONDREADS.out.extracted_diamond_reads
                .collect()
                .map { it -> file("${params.outdir}/extracted_reads/diamond") }
                .set { ch_diamond_output_dir }
        } else {
            diamond_output = diamond_taxpasta.join(diamond_tsv)
            DIAMOND_VIRAL_TAXID( params.evalue_threshold, diamond_output )
            diamond_taxids = DIAMOND_VIRAL_TAXID.out.viral_taxid
                .map { meta, taxid -> [ meta.subMap( meta.keySet() - 'tool' ), taxid ] }
                .splitText()

            diamond_combined_input = diamond_tsv.map{ meta, diamond_tsv -> [meta.subMap( meta.keySet() - 'tool' ), diamond_tsv ] }
                .join( reads, by:0 )
                .combine( diamond_taxids, by:0 )
                .multiMap { meta, diamond, reads, taxid ->
                    taxid: taxid.trim()
                    diamond_tsv: [ meta + [ taxid: taxid.trim() ], diamond, reads ]
                }

            EXTRACTDIAMONDREADS(
                diamond_combined_input.taxid,
                params.evalue_threshold,
                diamond_combined_input.diamond_tsv
            )
            ch_taxid_reads_diamond = EXTRACTDIAMONDREADS.out.extracted_diamond_reads
                .map {meta,reads -> [ meta+[tool:"diamond"], reads ]}
        }
        ch_taxid_reads         = ch_taxid_reads.mix(ch_taxid_reads_diamond)
    }

    emit:
    reads           = ch_taxid_reads       // channel: [ val (meta), [ reads ] ]
    versions        = ch_versions          // channel: [ versions.yml ]
}
