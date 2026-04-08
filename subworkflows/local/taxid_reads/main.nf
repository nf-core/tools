//
// EXTRACT READS
//

include { EXTRACT_VIRAL_TAXID as KRAKEN2_VIRAL_TAXID      } from '../../../modules/local/extract_viral_taxid'
include { EXTRACT_VIRAL_TAXID as CENTRIFUGE_VIRAL_TAXID   } from '../../../modules/local/extract_viral_taxid'
include { EXTRACT_VIRAL_TAXID as DIAMOND_VIRAL_TAXID      } from '../../../modules/local/extract_viral_taxid'
include { KRAKENTOOLS_EXTRACTKRAKENREADS                  } from '../../../modules/nf-core/krakentools/extractkrakenreads'
include { EXTRACTCENTRIFUGEREADS                          } from '../../../modules/local/extractcentrifugereads'
include { EXTRACTDIAMONDREADS                            } from '../../../modules/local/extractdiamondreads'

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

    ch_phages_taxid = params.phages_taxid ?
        channel.fromPath(params.phages_taxid, checkIfExists: true).first() :
        channel.value([])
    ch_taxid_list = params.taxid ?
        channel.fromPath(params.taxid, checkIfExists: true)
            .splitCsv(sep: '\t')
            .map { row ->
                def taxid = row[0]
                def species = row[1]
                    .replaceAll(/[^A-Za-z0-9]/, '-')  // Replace special chars with dashes
                    .replaceAll(/-+/, '-') // Replace multiple dashes with single dash
                    .replaceAll(/^-+|-+$/, '')        // Remove leading and trailing dashes
                [ taxid, species ]
            }
            .collect()
	    .map { it }
        : channel.value([])

    // Exyxtract kraken2 reads
    if ( params.extract_kraken2_reads ) {
        if ( params.taxid ) {
            kraken2_combined = kraken2_report.map { meta, kraken2_report -> [ meta.subMap(meta.keySet() - 'tool'), kraken2_report ] }
                .join (kraken2_result, by: 0)
                .join( reads, by: 0)
                .combine ( ch_taxid_list.flatten().collate(2))
                .multiMap { meta, kraken2_report, kraken2_result, reads, taxid, species  ->
                    def new_meta = meta + [ taxid: taxid, species: species]
                    taxid: taxid
                    kraken2_result: [ new_meta, kraken2_result ]
                    reads: [ new_meta, reads ]
                    kraken2_report: [ new_meta, kraken2_report ]
                }

            KRAKENTOOLS_EXTRACTKRAKENREADS(
                kraken2_combined.taxid,
                kraken2_combined.kraken2_result,
                kraken2_combined.reads,
                kraken2_combined.kraken2_report
            )
            ch_taxid_reads_kraken2  = KRAKENTOOLS_EXTRACTKRAKENREADS.out.extracted_kraken2_reads
                .map {meta,reads -> [ meta + [tool:"kraken2"], reads ]}
            ch_versions             = ch_versions.mix( KRAKENTOOLS_EXTRACTKRAKENREADS.out.versions.first() )
        } else {
            kraken2_output = kraken2_taxpasta.join(kraken2_report)
            KRAKEN2_VIRAL_TAXID( [], ch_phages_taxid, kraken2_output)

            kraken2_taxids = KRAKEN2_VIRAL_TAXID.out.viral_taxid
                .map { meta, taxid_list -> [ meta.subMap( meta.keySet() - 'tool' ), taxid_list ] }
                .splitCsv(sep: '\t')
                .map {meta, row -> [meta, row[0], row[1]]} //[meta, taxid, species]

            kraken2_combined = kraken2_result
                .join( reads, by:0)
                .join( kraken2_report.map { meta, kraken2_report -> [ meta.subMap(meta.keySet() - 'tool'), kraken2_report ]}, by:0 )
                .combine( kraken2_taxids, by:0 )
                .multiMap { meta, kraken2_result, reads, kraken2_report, taxid, species ->
                    def new_meta = meta + [ taxid: taxid, species: species ]
                    taxid: taxid.trim()
                    kraken2_result: [ new_meta, kraken2_result ]
                    reads: [ new_meta, reads ]
                    kraken2_report: [ new_meta, kraken2_report ]
                }

                KRAKENTOOLS_EXTRACTKRAKENREADS(
                kraken2_combined.taxid,
                kraken2_combined.kraken2_result,
                kraken2_combined.reads,
                kraken2_combined.kraken2_report
                )
            ch_taxid_reads_kraken2  = KRAKENTOOLS_EXTRACTKRAKENREADS.out.extracted_kraken2_reads
                .map {meta,reads -> [ meta+[tool: "kraken2"]+ [taxid: meta.taxid], reads ]}
        }
        ch_taxid_reads              = ch_taxid_reads.mix(ch_taxid_reads_kraken2)
    }

    // Extract centrifuge reads
    if ( params.extract_centrifuge_reads ) {
        if ( params.taxid ) {
            centrifuge_combined = centrifuge_result
                .join( reads, by: 0 )
                .combine ( ch_taxid_list.flatten().collate(2))
                .multiMap { meta, centrifuge_result, reads, taxid, species ->
                    taxid: taxid
                    centrifuge_result: [ meta + [taxid: taxid, species: species ], centrifuge_result, reads ]
                }

            EXTRACTCENTRIFUGEREADS(
                centrifuge_combined.taxid,
                centrifuge_combined.centrifuge_result
            )
            ch_taxid_reads_centrifuge  = EXTRACTCENTRIFUGEREADS.out.extracted_centrifuge_reads
                .map {meta,reads -> [ meta + [tool:"centrifuge"], reads ]}
            ch_versions                = ch_versions.mix( EXTRACTCENTRIFUGEREADS.out.versions )

        } else {
            centrifuge_output = centrifuge_taxpasta.join(centrifuge_report)
            CENTRIFUGE_VIRAL_TAXID( [], ch_phages_taxid, centrifuge_output )
            centrifuge_taxids = CENTRIFUGE_VIRAL_TAXID.out.viral_taxid
                .map { meta, taxid -> [ meta.subMap( meta.keySet() - 'tool' ), taxid ] }
                .splitCsv(sep: '\t')
                .map {meta, row -> [meta, row[0], row[1]]} //[meta, taxid, species]

            centrifuge_combined = centrifuge_result
                .join( reads, by:0 )
                .combine( centrifuge_taxids, by:0 )
                .multiMap { meta, centrifuge_result, reads, taxid, species ->
                    taxid: taxid.trim()
                    centrifuge_result: [ meta + [ taxid: taxid, species: species ], centrifuge_result, reads ]
                }

            EXTRACTCENTRIFUGEREADS(
                centrifuge_combined.taxid,
                centrifuge_combined.centrifuge_result
            )
            ch_taxid_reads_centrifuge  = EXTRACTCENTRIFUGEREADS.out.extracted_centrifuge_reads
                .map {meta,reads -> [ meta+[tool:"centrifuge"], reads ]}
        }
        ch_taxid_reads             = ch_taxid_reads.mix(ch_taxid_reads_centrifuge)
    }

    // Extract diamond reads
    if ( params.extract_diamond_reads ) {
        if ( params.taxid ) {
            diamond_combined = diamond_tsv.map { meta, diamond_tsv -> [meta.subMap( meta.keySet() - 'tool' ), diamond_tsv ] }
                .join( reads, by:0)
                .combine ( ch_taxid_list.flatten().collate(2))
                .multiMap { meta, diamond_tsv, reads, taxid, species ->
                    taxid: taxid
                    diamond_tsv: [ meta + [ taxid: taxid, species: species ], diamond_tsv, reads ]
                }

            EXTRACTDIAMONDREADS(
                diamond_combined.taxid,
                params.evalue_threshold,
                diamond_combined.diamond_tsv
            )
            ch_taxid_reads_diamond = EXTRACTDIAMONDREADS.out.extracted_diamond_reads
                .map {meta,reads -> [ meta+[tool:"diamond"], reads ]}
            ch_versions            = ch_versions.mix( EXTRACTDIAMONDREADS.out.versions )

        } else {
            diamond_output = diamond_taxpasta.join(diamond_tsv)
            DIAMOND_VIRAL_TAXID( params.evalue_threshold, ch_phages_taxid, diamond_output )
            diamond_taxids = DIAMOND_VIRAL_TAXID.out.viral_taxid
                .map { meta, taxid -> [ meta.subMap( meta.keySet() - 'tool' ), taxid ] }
                .splitCsv(sep: '\t')
                .map {meta, row -> [meta, row[0], row[1]]} //[meta, taxid, species]

            diamond_combined = diamond_tsv.map{ meta, diamond_tsv -> [meta.subMap( meta.keySet() - 'tool' ), diamond_tsv ] }
                .join( reads, by:0 )
                .combine( diamond_taxids, by:0 )
                .multiMap { meta, diamond, reads, taxid, species ->
                    taxid: taxid.trim()
                    diamond_tsv: [ meta + [ taxid: taxid, species: species ], diamond, reads ]
                }

            EXTRACTDIAMONDREADS(
                diamond_combined.taxid,
                params.evalue_threshold,
                diamond_combined.diamond_tsv
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
