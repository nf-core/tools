import org.everit.json.schema.Schema
import org.everit.json.schema.loader.SchemaLoader
import org.everit.json.schema.ValidationException
import org.json.JSONObject
import org.json.JSONTokener
import org.json.JSONArray
import groovy.json.JsonSlurper
import groovy.json.JsonBuilder

class Validation {

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
        Schema schema = SchemaLoader.load(rawSchema)

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
