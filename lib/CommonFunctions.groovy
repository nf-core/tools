/** This file holds several functions that can be used across many nf-core pipelines arbitrarily without having the main code in the pipelines specific repository in the future. Based on work by Patrick Huether (@phue), some updates and cleanup by (@apeltzer).
**/

@Grab('ch.qos.logback:logback-classic:1.2.3') 

import groovy.transform.CompileStatic
import groovy.json.JsonSlurper

@groovy.util.logging.Slf4j
//@CompileStatic
class CommonFunctions {

    private static Map generateLogColors(Boolean monochromeLogs) {
        Map colorcodes = [:]
        colorcodes['reset'] = monochromeLogs ? '' : "\033[0m"
        colorcodes['dim'] = monochromeLogs ? '' : "\033[2m"
        colorcodes['black'] = monochromeLogs ? '' : "\033[0;30m"
        colorcodes['green'] = monochromeLogs ? '' : "\033[0;32m"
        colorcodes['yellow'] = monochromeLogs ? '' :  "\033[0;33m"
        colorcodes['yellow_bold'] = monochromeLogs ? '' : "\033[1;93m"
        colorcodes['blue'] = monochromeLogs ? '' : "\033[0;34m"
        colorcodes['purple'] = monochromeLogs ? '' : "\033[0;35m"
        colorcodes['cyan'] = monochromeLogs ? '' : "\033[0;36m"
        colorcodes['white'] = monochromeLogs ? '' : "\033[0;37m"
        colorcodes['red'] = monochromeLogs ? '' : "\033[1;91m"
        return colorcodes
    }

    /*
    * This method tries to read the params file from JSON settings file given a path to a schema.
    * Can be directly used in the main.nf file to read in JSON schema and have a LinkedHashMap then with contents
    e.g. def paramsWithUsage = CommonFunctions.readParamsFromJsonSettings("$baseDir/nextflow_schema.json")
    */
    private static LinkedHashMap readParamsFromJsonSettings(String path) {
        def paramsWithUsage = new LinkedHashMap()
        try {
            paramsWithUsage = tryReadParamsFromJsonSettings(path)
        } catch (Exception e) {
            println "Could not read parameters settings from JSON. $e"
            paramsWithUsage = new LinkedHashMap()
        }
        return paramsWithUsage
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
    private static LinkedHashMap tryReadParamsFromJsonSettings(String path) throws Exception {
    
        def paramsContent = new File(path).text
        def Map paramsWithUsage = (Map) new JsonSlurper().parseText(paramsContent).get('properties')
        
        /* Tree looks like this in nf-core schema
        *  properties <- this is what the first get('properties') gets us
             group 1
               properties
               description
             group 2
               properties
               description
             group 3
               properties
               description
        */
        def output_map = new LinkedHashMap()
        
        //Lets go deeper
        paramsWithUsage.each { key, val ->
            //println "Group: $key\n" //Gets the Group names
            def Map submap = paramsWithUsage."$key".properties //Gets the property object of the group
            //println "Parameters:\n" //nested access to the Parameters
            def sub_params = new LinkedHashMap()
            submap.each { innerkey, value -> 
                //println "$innerkey\t$value.description"
                sub_params.put("$innerkey", "$value.description")
            }
            output_map.put("$key", sub_params)
            //println "\n"
        }
        return output_map
    }

    static String helpMessage(paramsWithUsage, workflow) {

        def usageHelp = String.format(
        """\
        Usage:
        The typical command for running the pipeline is as follows:
        nextflow run ${workflow.manifest.name} v${workflow.manifest.version} --input 'input.tsv' -profile docker
        Options:
        """.stripIndent(), println(prettyFormatJSON(paramsWithUsage)))
    }

    static String prettyFormatJSON(paramsWithUsage){
    //Todo make this really nicer ... this is just experimental code
        String output = ""
        for(group in paramsWithUsage.keySet()) {
            output += "Group: " + group + "\n"
            def params = paramsWithUsage.get(group) //This gets the parameters of that particular group
            for(par in params.keySet()) {
                output+= "\u001B[1m" + par + "\u001B[1m" + "\t" + params.get(par) + "\n"
            }
            output += "\n" //Extra newline after parameter block
        }
    
        return output
    }

    static String nfcoreHeader(params, workflow) {
        Map colors = generateLogColors(params.monochrome_logs)
        def showHeader = String.format(
        """\n
        ${colors.dim}----------------------------------------------------${colors.reset}
                                                ${colors.green},--.${colors.black}/${colors.green},-.${colors.reset}
        ${colors.blue}        ___     __   __   __   ___     ${colors.green}/,-._.--~\'${colors.reset}
        ${colors.blue}  |\\ | |__  __ /  ` /  \\ |__) |__         ${colors.yellow}}  {${colors.reset}
        ${colors.blue}  | \\| |       \\__, \\__/ |  \\ |___     ${colors.green}\\`-._,-`-,${colors.reset}
                                                ${colors.green}`._,._,\'${colors.reset}
        ${colors.purple}  ${workflow.manifest.name} v${workflow.manifest.version}${colors.reset}
        ${colors.dim}----------------------------------------------------${colors.reset}
        """.stripIndent())
    }
    static void checkHostname(params) {
        Map colors = generateLogColors(params.monochrome_logs)
        if(params.hostnames){
            def hostname = "hostname".execute().text.trim()
            params.hostnames.each { prof, hnames ->
                hnames.each { hname ->
                    if(hostname.contains(hname) && !workflow.profile.contains(prof)){
                        log.error "====================================================\n" +
                                "  ${colors.red}WARNING!${colors.reset} You are running with `-profile $workflow.profile`\n" +
                                "  but your machine hostname is ${colors.white}'$hostname'${colors.reset}\n" +
                                "  ${colors.yellow_bold}It's highly recommended that you use `-profile $prof${colors.reset}`\n" +
                                "============================================================"
                    }
                }
            }
        }
    }
    static void checkAWSbatch(params, workflow) {

        assert !params.awsqueue || !params.awsregion : "Specify correct --awsqueue and --awsregion parameters on AWSBatch!"
        // Check outdir paths to be S3 buckets if running on AWSBatch
        // related: https://github.com/nextflow-io/nextflow/issues/813
        assert !params.outdir.startsWith('s3:') : "Outdir not on S3 - specify S3 Bucket to run on AWSBatch!"
        // Prevent trace files to be stored on S3 since S3 does not support rolling files.
        assert workflow.tracedir.startsWith('s3:') :  "Specify a local tracedir or run without trace! S3 cannot be used for tracefiles."
    }
    static void workflowReport(summary, workflow, params, baseDir, mqc_report) {

        // Set up the e-mail variables
        def subject = "[$workflow.manifest.name] Successful: $workflow.runName"
        if(!workflow.success){
        subject = "[$workflow.manifest.name] FAILED: $workflow.runName"
        }
        def email_fields = [:]
        email_fields['version'] = workflow.manifest.version
        email_fields['runName'] = workflow.runName
        email_fields['success'] = workflow.success
        email_fields['dateComplete'] = workflow.complete
        email_fields['duration'] = workflow.duration
        email_fields['exitStatus'] = workflow.exitStatus
        email_fields['errorMessage'] = (workflow.errorMessage ?: 'None')
        email_fields['errorReport'] = (workflow.errorReport ?: 'None')
        email_fields['commandLine'] = workflow.commandLine
        email_fields['projectDir'] = workflow.projectDir
        email_fields['summary'] = summary
        email_fields['summary']['Date Started'] = workflow.start
        email_fields['summary']['Date Completed'] = workflow.complete
        email_fields['summary']['Pipeline script file path'] = workflow.scriptFile
        email_fields['summary']['Pipeline script hash ID'] = workflow.scriptId
        if(workflow.repository) email_fields['summary']['Pipeline repository Git URL'] = workflow.repository
        if(workflow.commitId) email_fields['summary']['Pipeline repository Git Commit'] = workflow.commitId
        if(workflow.revision) email_fields['summary']['Pipeline Git branch/tag'] = workflow.revision
        if(workflow.container) email_fields['summary']['Docker image'] = workflow.container
        email_fields['summary']['Nextflow Version'] = workflow.nextflow.version
        email_fields['summary']['Nextflow Build'] = workflow.nextflow.build
        email_fields['summary']['Nextflow Compile Timestamp'] = workflow.nextflow.timestamp

        // Render the TXT template
        def engine = new groovy.text.GStringTemplateEngine()
        def tf = new File("$baseDir/assets/email_template.txt")
        def txt_template = engine.createTemplate(tf).make(email_fields)
        def email_txt = txt_template.toString()

        // Render the HTML template
        def hf = new File("$baseDir/assets/email_template.html")
        def html_template = engine.createTemplate(hf).make(email_fields)
        def email_html = html_template.toString()

        // Render the sendmail template
        def smail_fields = [ email: params.email, subject: subject, email_txt: email_txt, email_html: email_html, baseDir: "$baseDir", mqcFile: mqc_report, mqcMaxSize: params.maxMultiqcEmailFileSize.toBytes() ]
        def sf = new File("$baseDir/assets/sendmail_template.txt")
        def sendmail_template = engine.createTemplate(sf).make(smail_fields)
        def sendmail_html = sendmail_template.toString()

        // Send the HTML e-mail
        if (params.email) {
            try {
            if( params.plaintext_email ){ throw GroovyException('Send plaintext e-mail, not HTML') }
            // Try to send HTML e-mail using sendmail
            [ 'sendmail', '-t' ].execute() << sendmail_html
            log.info "[$workflow.manifest.name] Sent summary e-mail to $params.email (sendmail)"
            } catch (all) {
            if (mqc_report.size() <= params.max_multiqc_email_size.toBytes() ) {
                [ 'mail', '-s', subject, params.email, '-A', mqc_report ].execute() << email_txt 
            } else {
            // Catch failures and try with plaintext
            [ 'mail', '-s', subject, params.email ].execute() << email_txt
            }
            log.info "[$workflow.manifest.name] Sent summary e-mail to $params.email (mail)"
            }
        }

        // Write summary e-mail HTML to a file
        def output_d = new File( "${params.outdir}/pipeline_info/" )
        if( !output_d.exists() ) {
        output_d.mkdirs()
        }
        def output_hf = new File( output_d, "pipeline_report.html" )
        output_hf.withWriter { w -> w << email_html }
        def output_tf = new File( output_d, "pipeline_report.txt" )
        output_tf.withWriter { w -> w << email_txt }

        Map colors = generateLogColors(params.monochrome_logs)

        if (workflow.stats.ignoredCountFmt > 0 && workflow.success) {
            log.info "${colors.purple}Warning, pipeline completed, but with errored process(es) ${colors.reset}"
            log.info "${colors.red}Number of ignored errored process(es) : ${workflow.stats.ignoredCountFmt} ${colors.reset}"
            log.info "${colors.green}Number of successfully ran process(es) : ${workflow.stats.succeedCountFmt} ${colors.reset}"
        }

        if (workflow.success) {
            log.info "${colors.purple}[$workflow.manifest.name]${colors.green} Pipeline completed successfully${colors.reset}"
        } else {
            checkHostname(params)
            log.info "${colors.purple}[$workflow.manifest.name]${colors.red} Pipeline completed with errors${colors.reset}"
        }
    }
}

