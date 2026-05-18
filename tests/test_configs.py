INFRA_SINGULARITY_CONFIG = """\
params {
    config_profile_contact = 'my name (@myhandle)'
    config_profile_description = 'A cool description'
    config_profile_url = 'https://example.com'
    igenomes_base = '/data/igenomes/cache'
}
executor {
    queueStatInterval = '0.75m'
    queueSize = 200
    pollInterval = '0.25m'
    submitRateLimit = '25min'
}
process {
    executor = 'pbspro'
    queue = 'myqueue'
    resourceLimits = [cpus: 48, memory: '128.0GB', time: '9.5h']
    scratch = '/tmp/scratch'
    maxRetries = 2
}
singularity {
    enabled = true
    cacheDir = '/singularity/cachedir'
    autoMounts = true
}
cleanup = true
"""

INFRA_CUSTOM_SINGULARITY_CONFIG = """\
params {
    config_profile_description = 'A cool description'
}
executor {
    queueStatInterval = '0.75m'
    queueSize = 200
    pollInterval = '0.25m'
    submitRateLimit = '25min'
}
process {
    executor = 'pbspro'
    queue = 'myqueue'
    resourceLimits = [cpus: 48, memory: '128.0GB', time: '9.5h']
    scratch = '/tmp/scratch'
    maxRetries = 2
}
singularity {
    enabled = true
    cacheDir = '/singularity/cachedir'
    autoMounts = true
}
cleanup = true
"""

PIPE_NFCORE_CONFIG = """\
params {
    config_profile_contact = 'my name (@myhandle)'
    config_profile_description = 'A cool description'
    config_profile_url = 'https://example.com'
}
process {
    cpus = 2
    memory = '8.0GB'
    time = '9.5h'
    withName: 'SOME:PROC.NAME*' {
        cpus = 3
        memory = '4.0GB'
        time = '5.5h'
    }
    withName: 'ANOTHER:PROC_NAME' {
        cpus = 2
        memory = '3.0GB'
        time = '4.4h'
        queue = 'customqueue'
    }
    withLabel: 'some_proc_label' {
        cpus = 1
        memory = '1.0GB'
        time = '1.1h'
    }
    withLabel: 'another_label' {
        cpus = 2
        memory = '2.0GB'
        time = '2.2h'
        queue = 'customqueue'
    }
    withLabel: 'a_third_label' {
    }
    withLabel: 'fourth_label' {
        cpus = 4
        time = '4.4h'
        queue = 'anotherqueue'
    }
}
"""

PIPE_CUSTOM_CONFIG = """\
params {
    config_profile_description = 'A cool description'
}
process {
    cpus = 2
    memory = '8.0GB'
    time = '9.5h'
    withName: 'some_proc' {
        cpus = 3
        memory = '4.0GB'
        time = '5.5h'
    }
    withName: 'another_proc' {
        cpus = 2
        memory = '3.0GB'
        time = '4.4h'
        queue = 'customqueue'
    }
    withLabel: 'some_proc_label' {
        cpus = 1
        memory = '1.0GB'
        time = '1.1h'
    }
    withLabel: 'another_label' {
        cpus = 2
        memory = '2.0GB'
        time = '2.2h'
        queue = 'customqueue'
    }
    withLabel: 'a_third_label' {
    }
    withLabel: 'fourth_label' {
        cpus = 4
        time = '4.4h'
        queue = 'anotherqueue'
    }
}
"""