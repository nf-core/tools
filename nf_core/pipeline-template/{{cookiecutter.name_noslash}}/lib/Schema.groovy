/*
 * This file holds several functions used to perform JSON parameter validation, help and summary rendering for the nf-core pipeline template.
 */

import org.everit.json.schema.Schema as JsonSchema
import org.everit.json.schema.loader.SchemaLoader
import org.everit.json.schema.ValidationException
import org.json.JSONObject
import org.json.JSONTokener
import org.json.JSONArray
import groovy.json.JsonSlurper
import groovy.json.JsonBuilder

class Schema {

    /*
     * This method tries to read a JSON params file
     */
    private static LinkedHashMap params_load(String json_schema) {
        def params_map = new LinkedHashMap()
        try {
            params_map = params_read(json_schema)
        } catch (Exception e) {
            println "Could not read parameters settings from JSON. $e"
            params_map = new LinkedHashMap()
        }
        return params_map
    }

    /*
    Method to actually read in JSON file using Groovy.
    Group (as Key), values are all parameters
        - Parameter1 as Key, Description as Value
        - Parameter2 as Key, Description as Value
        ....
    Group
        -
    */
    private static LinkedHashMap params_read(String json_schema) throws Exception {
        def json = new File(json_schema).text
        def Map json_params = (Map) new JsonSlurper().parseText(json).get('definitions')
        /* Tree looks like this in nf-core schema
         * definitions <- this is what the first get('definitions') gets us
             group 1
               title
               description
                 properties
                   parameter 1
                     type
                     description
                   parameter 2
                     type
                     description
             group 2
               title
               description
                 properties
                   parameter 1
                     type
                     description
        */
        def params_map = new LinkedHashMap()
        json_params.each { key, val ->
            def Map group = json_params."$key".properties // Gets the property object of the group
            def title = json_params."$key".title
            def sub_params = new LinkedHashMap()
            group.each { innerkey, value ->
                sub_params.put(innerkey, value)
            }
            params_map.put(title, sub_params)
        }
        return params_map
    }

    /*
     * Get maximum number of characters across all parameter names
     */
    private static Integer params_max_chars(params_map) {
        Integer max_chars = 0
        for (group in params_map.keySet()) {
            def group_params = params_map.get(group)  // This gets the parameters of that particular group
            for (param in group_params.keySet()) {
                if (param.size() > max_chars) {
                    max_chars = param.size()
                }
            }
        }
        return max_chars
    }

    /*
     * Beautify parameters for --help
     */
    private static String params_help(workflow, params, json_schema, command) {
        String output  = Headers.nf_core(workflow, params.monochrome_logs) + '\n'
        output        += 'Typical pipeline command:\n\n'
        output        += "    ${command}\n\n"
        def params_map = params_load(json_schema)
        def max_chars  = params_max_chars(params_map) + 1
        for (group in params_map.keySet()) {
            output += group + '\n'
            def group_params = params_map.get(group)  // This gets the parameters of that particular group
            for (param in group_params.keySet()) {
                def type = '[' + group_params.get(param).type + ']'
                def description = group_params.get(param).description
                output += "    \u001B[1m--" +  param.padRight(max_chars) + "\u001B[1m" + type.padRight(10) + description + '\n'
            }
            output += '\n'
        }
        output += Headers.dashed_line(params.monochrome_logs)
        output += '\n\n' + Checks.citation(workflow)
        output += '\n\n' + Headers.dashed_line(params.monochrome_logs)
        return output
    }

    /*
     * Groovy Map summarising parameters/workflow options used by the pipeline
     */
    private static LinkedHashMap params_summary_map(workflow, params, json_schema) {
        // Get a selection of core Nextflow workflow options
        def Map workflow_summary = [:]
        if (workflow.revision) {
            workflow_summary['revision'] = workflow.revision
        }
        workflow_summary['runName']      = workflow.runName
        if (workflow.containerEngine) {
            workflow_summary['containerEngine'] = "$workflow.containerEngine"
        }
        if (workflow.container) {
            workflow_summary['container']       = "$workflow.container"
        }
        workflow_summary['launchDir']    = workflow.launchDir
        workflow_summary['workDir']      = workflow.workDir
        workflow_summary['projectDir']   = workflow.projectDir
        workflow_summary['userName']     = workflow.userName
        workflow_summary['profile']      = workflow.profile
        workflow_summary['configFiles']  = workflow.configFiles.join(', ')

        // Get pipeline parameters defined in JSON Schema
        def Map params_summary = [:]
        def blacklist  = ['hostnames']
        def params_map = params_load(json_schema)
        for (group in params_map.keySet()) {
            def sub_params = new LinkedHashMap()
            def group_params = params_map.get(group)  // This gets the parameters of that particular group
            for (param in group_params.keySet()) {
                if (params.containsKey(param) && !blacklist.contains(param)) {
                    def params_value = params.get(param)
                    def schema_value = group_params.get(param).default
                    def param_type   = group_params.get(param).type
                    if (schema_value == null) {
                        if (param_type == 'boolean') {
                            schema_value = false
                        }
                        if (param_type == 'string') {
                            schema_value = ''
                        }
                        if (param_type == 'integer') {
                            schema_value = 0
                        }
                    } else {
                        if (param_type == 'string') {
                            if (schema_value.contains('$baseDir') || schema_value.contains('${baseDir}')) {
                                def sub_string = schema_value.replace('\$baseDir', '')
                                sub_string     = sub_string.replace('\${baseDir}', '')
                                if (params_value.contains(sub_string)) {
                                    schema_value = params_value
                                }
                            }
                            if (schema_value.contains('$params.outdir') || schema_value.contains('${params.outdir}')) {
                                def sub_string = schema_value.replace('\$params.outdir', '')
                                sub_string     = sub_string.replace('\${params.outdir}', '')
                                if ("${params.outdir}${sub_string}" == params_value) {
                                    schema_value = params_value
                                }
                            }
                        }
                    }

                    if (params_value != schema_value) {
                        sub_params.put("$param", params_value)
                    }
                }
            }
            params_summary.put(group, sub_params)
        }
        return [ 'Core Nextflow options' : workflow_summary ] << params_summary
    }

    /*
     * Beautify parameters for summary and return as string
     */
    private static String params_summary_log(workflow, params, json_schema) {
        String output  = Headers.nf_core(workflow, params.monochrome_logs) + '\n'
        def params_map = params_summary_map(workflow, params, json_schema)
        def max_chars  = params_max_chars(params_map)
        for (group in params_map.keySet()) {
            def group_params = params_map.get(group)  // This gets the parameters of that particular group
            if (group_params) {
                output += group + '\n'
                for (param in group_params.keySet()) {
                    output += "    \u001B[1m" +  param.padRight(max_chars) + ": \u001B[1m" + group_params.get(param) + '\n'
                }
                output += '\n'
            }
        }
        output += Headers.dashed_line(params.monochrome_logs)
        output += '\n\n' + Checks.citation(workflow)
        output += '\n\n' + Headers.dashed_line(params.monochrome_logs)
        return output
    }

    static String params_summary_multiqc(workflow, summary) {
        String summary_section = ''
        for (group in summary.keySet()) {
            def group_params = summary.get(group)  // This gets the parameters of that particular group
            if (group_params) {
                summary_section += "    <p style=\"font-size:110%\"><b>$group</b></p>\n"
                summary_section += "    <dl class=\"dl-horizontal\">\n"
                for (param in group_params.keySet()) {
                    summary_section += "        <dt>$param</dt><dd><samp>${group_params.get(param) ?: '<span style=\"color:#999999;\">N/A</a>'}</samp></dd>\n"
                }
                summary_section += '    </dl>\n'
            }
        }

        String yaml_file_text  = "id: '${workflow.manifest.name.replace('/', '-')}-summary'\n"
        yaml_file_text        += "description: ' - this information is collected when the pipeline is started.'\n"
        yaml_file_text        += "section_name: '${workflow.manifest.name} Workflow Summary'\n"
        yaml_file_text        += "section_href: 'https://github.com/${workflow.manifest.name}'\n"
        yaml_file_text        += "plot_type: 'html'\n"
        yaml_file_text        += 'data: |\n'
        yaml_file_text        += "${summary_section}"
        return yaml_file_text
    }

    /*
    * Function to loop over all parameters defined in schema and check
    * whether the given paremeters adhere to the specificiations
    */
    /* groovylint-disable-next-line UnusedPrivateMethodParameter */
    private static ArrayList validateParameters(params, jsonSchema, log) {
        //=====================================================================//
        // Validate parameters against the schema
        InputStream inputStream = new File(jsonSchema).newInputStream()
        JSONObject rawSchema = new JSONObject(new JSONTokener(inputStream))
        JsonSchema schema = SchemaLoader.load(rawSchema)

        // Clean the parameters
        def cleanedParams = cleanParameters(params)

        // Convert to JSONObject
        def jsonParams = new JsonBuilder(cleanedParams)
        JSONObject paramsJSON = new JSONObject(jsonParams.toString())

        // Validate
        try {
            schema.validate(paramsJSON)
        } catch (ValidationException e) {
            log.error 'Found parameter violations!'
            JSONObject exceptionJSON = e.toJSON()
            printExceptions(exceptionJSON, log)
            System.exit(1)
        }

        // Check for nextflow core params and unexpected params
        def json = new File(jsonSchema).text
        def Map schemaParams = (Map) new JsonSlurper().parseText(json).get('definitions')
        def specifiedParamKeys = params.keySet()
        def nf_params = ['profile', 'config', 'c', 'C', 'syslog', 'd', 'dockerize',
                        'bg', 'h', 'log', 'quiet', 'q', 'v', 'version']
        def unexpectedParams = []

        // Collect expected parameters from the schema
        def expectedParams = []
        for (group in schemaParams) {
            for (p in group.value['properties']) {
                expectedParams.push(p.key)
            }
        }

        for (specifiedParam in specifiedParamKeys) {
            // nextflow params
            if (nf_params.contains(specifiedParam)) {
                log.error "ERROR: You used a core Nextflow option with two hyphens: --${specifiedParam}! Please resubmit with one."
                System.exit(1)
            }
            // unexpected params
            if (!expectedParams.contains(specifiedParam)) {
                unexpectedParams.push(specifiedParam)
            }
        }

        return unexpectedParams
    }

    // Loop over nested exceptions and print the causingException
    private static void printExceptions(exJSON, log) {
        def causingExceptions = exJSON['causingExceptions']
        if (causingExceptions.length() == 0) {
            log.error "${exJSON['message']} ${exJSON['pointerToViolation']}"
        }
        else {
            log.error exJSON['message']
            for (ex in causingExceptions) {
                printExceptions(ex, log)
            }
        }
    }

    private static Map cleanParameters(params) {
        def new_params = params.getClass().newInstance(params)
        for (p in params) {
            // remove anything evaluating to false
            if (!p['value']) {
                new_params.remove(p.key)
            }
            // Cast MemoryUnit to String
            if (p['value'].getClass() == nextflow.util.MemoryUnit) {
                new_params.replace(p.key, p['value'].toString())
            }
            // Cast Duration to String
            if (p['value'].getClass() == nextflow.util.Duration) {
                new_params.replace(p.key, p['value'].toString())
            }
            // Cast LinkedHashMap to String
            if (p['value'].getClass() == LinkedHashMap) {
                new_params.replace(p.key, p['value'].toString())
            }
        }
        return new_params
    }

}
