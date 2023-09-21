//
// This file holds several functions specific to the main.nf workflow in the {{ name }} pipeline
//

class WorkflowMain {

    {%- if igenomes %}
    //
    // Get attribute from genome config file e.g. fasta
    //
    public static Object getGenomeAttribute(params, attribute) {
        if (params.genomes && params.genome && params.genomes.containsKey(params.genome)) {
            if (params.genomes[ params.genome ].containsKey(attribute)) {
                return params.genomes[ params.genome ][ attribute ]
            }
        }
        return null
    }
    {%- endif %}
}
