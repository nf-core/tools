import groovy.json.JsonSlurper
import groovy.util.logging.Log

class Validation {

    /*
    * Function to loop over all parameters defined in schema and check
    * whether the given paremeters adhere to the specificiations
    */
    private static void validateParameters(params, json_schema, log, workflow){

        def json = new File(json_schema).text
        def Map json_params = (Map) new JsonSlurper().parseText(json).get('definitions')
        def specified_param_keys = params.keySet()
        def nf_params = ['profile', 'config', 'c', 'C', 'syslog', 'd', 'dockerize', 
                        'bg', 'h', 'log', 'quiet', 'q', 'v', 'version']
        def valid_params = []
        def expected_params = []
        def blacklist  = ['hostnames'] // ignored parameters
        

        // Loop over all parameters in schema and compare to given parameters
        for (group in json_params){
            for (p in group.value['properties']){
                if (!blacklist.contains(p.key)){
                    valid_params.push(validateParamPair(params[p.key], p, log))
                    expected_params.push(p.key)
                }
            }
        }

        // Exit if any invalid params where found
        if (valid_params.contains(false)){
            System.exit(0)
        }

        // Check for nextflow core params and unexpected params
        for (specified_param in specified_param_keys){
            // nextflow params
            if (nf_params.contains(specified_param)){
                log.error "ERROR: You have overwritten the core Nextflow parameter -${specified_param} with --${specified_param}!"
                System.exit(0)
            }
            // unexpected params
            if (!expected_params.contains(specified_param)){
                log.warn "Unexpected parameter specified: ${specified_param}"               
            }
            
        }

    }



    /*
    * Compare a pair of params (schema, command line) and check whether 
    * they are valid
    */
     private static boolean validateParamPair(given_param, json_param, log){
        def param_type = json_param.value['type']
        def valid_param = true
        def required = json_param.value['required']
        def param_enum = json_param.value['enum']
        def param_pattern = json_param.value['pattern']
        
        // Check only if required or parameter is given
        if (required || given_param){
            def given_param_class = given_param.getClass()

                switch(param_type) {
                    case 'string':
                        // If pattern given, check that param adheres to it
                        if (param_pattern){
                            valid_param = given_param ==~ param_pattern
                        } 
                        // If enum given, check that param is within choices
                        else if (param_enum){
                            valid_param = param_enum.contains(given_param)
                        }
                        // else just check whether valid String
                        else {
                            valid_param = given_param_class == String
                        } 
                        break
                    case 'boolean':
                        if (given_param_class == Boolean){
                            valid_param = true
                        }
                        else if (given_param){
                            valid_param = true
                        }
                        break
                    case 'integer':
                        valid_param = given_param_class == Integer
                        break
                    case 'number':
                        valid_param = given_param_class == BigDecimal
                        break
                }

            if (!valid_param){
                log.error "ERROR: Parameter ${json_param.key} is wrong type! Expected ${param_type}, found ${given_param_class}, ${given_param}"
                if (param_enum){
                    log.error "Must be one of: ${param_enum}"
                }
                if (param_pattern){
                    log.error "Parameter must adhere to the following pattern: ${param_pattern}"
                }
            }

        }
        return valid_param
     }

}