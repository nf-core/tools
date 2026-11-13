{% if repo_type == "modules" and org == "nf-core" -%}
// Copyright (c) the nf-core community under an open-source MIT license.
// See https://github.com/nf-core/modules for full license, file patching instructions and upstream contributing.
{% endif -%}
{%- if with_records -%}
{{ '\n' if repo_type == "modules" and org == "nf-core" }}nextflow.enable.types = true
{%- if not_empty_template %}

// TODO nf-core: If in doubt look at other nf-core/modules to see how we are doing things! :)
//               https://github.com/nf-core/modules/tree/master/modules/nf-core/
//               You can also ask for help via your pull request or on the #modules channel on the nf-core Slack workspace:
//               https://nf-co.re/join
// TODO nf-core: A module MUST take exactly one record as input and emit exactly one record as output.
//               See https://nf-co.re/blog/2026/types-and-records for the reasoning behind this structure.
// TODO nf-core: Tool arguments MUST be passed via the `<tool>_args` input field (pipeline developers)
//               or `ext.args` (pipeline users), never hardcoded.
// TODO nf-core: Software that can be piped together SHOULD be added to separate module files
//               unless there is a run-time, storage advantage in implementing in this way
//               e.g. it's ok to have a single module for bwa to output BAM instead of SAM:
//                 bwa mem | samtools view -B -T ref.fasta
{%- endif %}

process {{ component_name_underscore|upper }} {
    tag "${id}"
    label '{{ process_label }}'

    {% if not_empty_template -%}
    // TODO nf-core: See section in main README for further information regarding finding and adding container addresses to the section below.
    {% endif -%}
    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        '{{ singularity_container if singularity_container else 'https://depot.galaxyproject.org/singularity/YOUR-TOOL-HERE' }}':
        '{{ 'quay.io/' + docker_container if docker_container else 'quay.io/biocontainers/YOUR-TOOL-HERE' }}' }"

    {% if not_empty_template -%}
    // TODO nf-core: Priority is `ext.<var>` from a user config > input record field > default below.
    //               Add one `<tool>_args` entry per tool used in the module.
    {% endif -%}
    ext [
        prefix: { output_prefix ?: "${id}" },
        args: { {{ component_name_underscore|lower }}_args ?: '' }
    ]

    input:
    {%- if not_empty_template %}
    // TODO nf-core: Add every value and file the process needs as a typed field of this record.
    //               Mandatory sample information (e.g. `single_end`, `strandedness`) MUST be a top-level field, not read from `meta`.
    //               Use `Path` for a single file and `Set<Path>`, `List<Path>` or `Bag<Path>` for multiple files.
    //               Mark optional fields with `?` after the type, e.g. `Path?`.
    // TODO nf-core: Where applicable please provide/convert compressed files as input/output
    //               e.g. "*.fastq.gz" and NOT "*.fastq", "*.bam" and NOT "*.sam" etc.
    {%- endif %}
    {%- if inputs %}
    // TODO nf-core: Update the information obtained from bio.tools and make sure that it is correct
    {%- endif %}
    record(
        id: String,
        meta: Record?,
        {%- for name in record_inputs %}
        {{ name }}: Path,
        {%- endfor %}
        {{ component_name_underscore|lower }}_args: String?,
        output_prefix: String?
    )

    output:
    {%- if outputs %}
    // TODO nf-core: Update the information obtained from bio.tools and make sure that it is correct
    {%- elif not_empty_template %}
    // TODO nf-core: Add a field for ALL output files, using `optional: true` for files that may not be produced
    {%- endif %}
    record(
        id: id,
        meta: meta,
        {%- for name, field in record_outputs.items() %}
        {{ name }}: {{ field.value }}{{ ',' if not loop.last }}
        {%- endfor %}
    )

    topic:
    {%- if not_empty_template %}
    // TODO nf-core: Update the command here to obtain the version number of the software used in this module
    // TODO nf-core: If multiple software packages are used in this module, all MUST be added here
    //               by copying the line below and replacing the current tool with the extra tool(s)
    {%- endif %}
    record(process: "${task.process}", tool: '{{ component }}', version: eval("{{ component }} --version")) >> 'versions'

    script:
    {%- if not_empty_template %}
    // TODO nf-core: If the tool supports multi-threading then you MUST provide the appropriate parameter
    //               using the Nextflow "task" variable e.g. "--threads ${task.cpus}"
    // TODO nf-core: Please replace the example samtools command below with your module's command
    // TODO nf-core: Please indent the command appropriately (4 spaces!!) to help with readability ;)
    {%- endif %}
    """
    {% if not_empty_template -%}
    {{ component }} \\
        ${task.ext.args} \\
        -@ ${task.cpus} \\
        {%- for field in record_outputs.values() %}
        {%- for ext in field.ontologies[2] %}
        -o ${task.ext.prefix}.{{ ext }} \\
        {%- endfor %}
        {%- endfor %}
        {%- for name in record_inputs %}
        ${{ '{' + name + '}' }}{{ ' \\\\' if not loop.last }}
        {%- endfor %}
    {%- endif %}
    """

    stub:
    {%- if not_empty_template %}
    // TODO nf-core: A stub section should mimic the execution of the original module as best as possible
    //               Have a look at the following examples:
    //               Simple example: https://github.com/nf-core/modules/blob/624977dfaf562211e68a8a868ca80acc8461f1ac/modules/nf-core/cutadapt/main.nf#L34-L46
    //               Complex example: https://github.com/nf-core/modules/blob/88d43dad73a675e66bff49ebb57fe657a5909018/modules/nf-core/bedtools/split/main.nf#L32-L43
    {%- endif %}
    """
    echo ${task.ext.args}
    {%- if not_empty_template %}
    {%- for field in record_outputs.values() %}
    {%- for ext in field.ontologies[2] %}
    touch ${task.ext.prefix}.{{ ext }}
    {%- endfor %}
    {%- endfor %}
    {%- endif %}
    """
}
{%- else -%}
{%- if not_empty_template -%}
// TODO nf-core: If in doubt look at other nf-core/modules to see how we are doing things! :)
//               https://github.com/nf-core/modules/tree/master/modules/nf-core/
//               You can also ask for help via your pull request or on the #modules channel on the nf-core Slack workspace:
//               https://nf-co.re/join
// TODO nf-core: A module file SHOULD only define input and output files as command-line parameters.
//               All other parameters MUST be provided using the "task.ext" directive, see here:
//               https://www.nextflow.io/docs/latest/process.html#ext
//               where "task.ext" is a string.
//               Any parameters that need to be evaluated in the context of a particular sample
//               e.g. single-end/paired-end data MUST also be defined and evaluated appropriately.
// TODO nf-core: Software that can be piped together SHOULD be added to separate module files
//               unless there is a run-time, storage advantage in implementing in this way
//               e.g. it's ok to have a single module for bwa to output BAM instead of SAM:
//                 bwa mem | samtools view -B -T ref.fasta
// TODO nf-core: Optional inputs are not currently supported by Nextflow. However, using an empty
//               list (`[]`) instead of a file can be used to work around this issue.
{% endif %}
process {{ component_name_underscore|upper }} {
    tag {{ '"$meta.id"' if has_meta else "'$bam'" }}
    label '{{ process_label }}'

    {% if not_empty_template -%}
    // TODO nf-core: See section in main README for further information regarding finding and adding container addresses to the section below.
    {% endif -%}
    conda "${moduleDir}/environment.yml"
    container "${ workflow.containerEngine in ['singularity', 'apptainer'] && !task.ext.singularity_pull_docker_container ?
        '{{ singularity_container if singularity_container else 'https://depot.galaxyproject.org/singularity/YOUR-TOOL-HERE' }}':
        '{{ 'quay.io/' + docker_container if docker_container else 'quay.io/biocontainers/YOUR-TOOL-HERE' }}' }"

    input:
    {%- if inputs %}
    // TODO nf-core: Update the information obtained from bio.tools and make sure that it is correct
    {%- for input_name, ontologies in inputs.items() %}
    {% set meta_index = loop.index|string if not loop.first else '' %}
    {{ 'tuple val(meta' + meta_index + '), path(' + input_name + ')' if has_meta else 'path ' + input_name }}
    {%- endfor %}
    {%- else -%}
    {% if not_empty_template -%}
    // TODO nf-core: Where applicable all sample-specific information e.g. "id", "single_end", "read_group"
    //               MUST be provided as an input via a Groovy Map called "meta".
    //               This information may not be required in some instances e.g. indexing reference genome files:
    //               https://github.com/nf-core/modules/blob/master/modules/nf-core/bwa/index/main.nf
    // TODO nf-core: Where applicable please provide/convert compressed files as input/output
    //               e.g. "*.fastq.gz" and NOT "*.fastq", "*.bam" and NOT "*.sam" etc.
    {{ 'tuple val(meta), path(bam)' if has_meta else 'path bam' }}
    {%- else -%}
    {{ 'tuple val(meta), path(input)' if has_meta else 'path input' }}
    {%- endif %}
    {%- endif %}

    output:
    {%- if outputs %}
    // TODO nf-core: Update the information obtained from bio.tools and make sure that it is correct
    {%- for output_name, ontologies in outputs.items() %}
    {{ 'tuple val(meta), path("*.{' + ontologies[2]|join(',') + '}")' if has_meta else 'path ' + output_name }}, emit: {{ output_name }}
    {%- endfor %}
    {%- else %}
    {% if not_empty_template -%}
    // TODO nf-core: Named file extensions MUST be emitted for ALL output channels
    {{ 'tuple val(meta), path("*.bam")' if has_meta else 'path "*.bam"' }}, emit: bam
    // TODO nf-core: List additional required output channels/values here
    {%- else -%}
    {{ 'tuple val(meta), path("*")' if has_meta else 'path "*"' }}, emit: output
    {%- endif %}
    {%- endif %}
    {% if not_empty_template -%}
    // TODO nf-core: Update the command here to obtain the version number of the software used in this module
    // TODO nf-core: If multiple software packages are used in this module, all MUST be added here
    //               by copying the line below and replacing the current tool with the extra tool(s)
    {%- endif %}
    tuple val("${task.process}"), val('{{ component }}'), eval("{{ component }} --version"), topic: versions, emit: versions_{{ component }}

    when:
    task.ext.when == null || task.ext.when

    script:
    def args = task.ext.args ?: ''
    {% if has_meta -%}
    def prefix = task.ext.prefix ?: "${meta.id}"
    {%- endif %}
    {% if not_empty_template -%}
    // TODO nf-core: Where possible, a command MUST be provided to obtain the version number of the software e.g. 1.10
    //               If the software is unable to output a version number on the command-line then it can be manually specified
    //               e.g. https://github.com/nf-core/modules/blob/master/modules/nf-core/homer/annotatepeaks/main.nf
    //               Each software used MUST provide the software name and version number in the YAML version file (versions.yml)
    // TODO nf-core: It MUST be possible to pass additional parameters to the tool as a command-line string via the "task.ext.args" directive
    // TODO nf-core: If the tool supports multi-threading then you MUST provide the appropriate parameter
    //               using the Nextflow "task" variable e.g. "--threads $task.cpus"
    // TODO nf-core: Please replace the example samtools command below with your module's command
    // TODO nf-core: Please indent the command appropriately (4 spaces!!) to help with readability ;)
    {%- endif %}
    """
    {% if not_empty_template -%}
    {{ component }} \\
        $args \\
        -@ $task.cpus \\
        {%- if has_meta %}
        {%- if inputs %}
        {%- for input_name, ontologies in inputs.items() %}
        {%- set extensions = ontologies[2] %}
        {%- for ext in extensions %}
        -o ${prefix}.{{ ext }} \\
        {%- endfor %}
        {%- endfor %}
        {%- else %}
        -o ${prefix}.bam \\
        {%- endif %}
        {%- endif %}
        {%- if inputs %}
        {%- for input_name, ontologies in inputs.items() %}
        ${{ input_name }} \\
        {%- endfor %}
        {%- else %}
        $bam
        {%- endif %}
    {%- endif %}
    """

    stub:
    def args = task.ext.args ?: ''
    {% if has_meta -%}
    def prefix = task.ext.prefix ?: "${meta.id}"
    {%- endif %}
    {% if not_empty_template -%}
    // TODO nf-core: A stub section should mimic the execution of the original module as best as possible
    //               Have a look at the following examples:
    //               Simple example: https://github.com/nf-core/modules/blob/624977dfaf562211e68a8a868ca80acc8461f1ac/modules/nf-core/cutadapt/main.nf#L34-L46
    //               Complex example: https://github.com/nf-core/modules/blob/88d43dad73a675e66bff49ebb57fe657a5909018/modules/nf-core/bedtools/split/main.nf#L32-L43
    // TODO nf-core: If the module doesn't use arguments ($args), you SHOULD remove:
    //               - The definition of args `def args = task.ext.args ?: ''` above.
    //               - The use of the variable in the script `echo $args ` below.
    {%- endif %}
    """
    echo $args
    {% if not_empty_template -%}
    {%- if inputs %}
    {%- for input_name, ontologies in inputs.items() %}
    {%- set extensions = ontologies[2] %}
    {%- for ext in extensions %}
    touch ${prefix}.{{ ext }}
    {%- endfor %}
    {%- endfor %}
    {%- else %}
    touch ${prefix}.bam
    {%- endif %}
    {%- endif %}
    """
}
{%- endif %}
