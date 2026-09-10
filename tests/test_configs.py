INFRA_SINGULARITY_CONFIG = """\
params {
    config_profile_contact = 'my name (@myhandle)'
    config_profile_description = 'A cool description'
    config_profile_url = 'https://example.com'
    igenomes_base = '/data/igenomes/cache'
}
executor {
    queueStatInterval = '45 s'
    queueSize = 200
    pollInterval = '15 s'
    submitRateLimit = '25 min'
}
process {
    executor = 'pbspro'
    queue = 'myqueue'
    resourceLimits = [cpus: 48, memory: '128 GB', time: '9.5 h']
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
    queueStatInterval = '45 s'
    queueSize = 200
    pollInterval = '15 s'
    submitRateLimit = '25 min'
}
process {
    executor = 'pbspro'
    queue = 'myqueue'
    resourceLimits = [cpus: 48, memory: '128 GB', time: '9.5 h']
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
    memory = '8 GB'
    time = '9.5 h'
    withName: 'SOME:PROC.NAME*' {
        cpus = 3
        memory = '4 GB'
        time = '5.5 h'
    }
    withName: 'ANOTHER:PROC_NAME' {
        cpus = 2
        memory = '3 GB'
        time = '4.4 h'
        queue = 'customqueue'
    }
    withLabel: 'some_proc_label' {
        cpus = 1
        memory = '1 GB'
        time = '1.1 h'
    }
    withLabel: 'another_label' {
        cpus = 2
        memory = '2 GB'
        time = '2.2 h'
        queue = 'customqueue'
    }
    withLabel: 'fourth_label' {
        cpus = 4
        time = '4.4 h'
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
    memory = '8 GB'
    time = '9.5 h'
    withName: 'some_proc' {
        cpus = 3
        memory = '4 GB'
        time = '5.5 h'
    }
    withName: 'another_proc' {
        cpus = 2
        memory = '3 GB'
        time = '4.4 h'
        queue = 'customqueue'
    }
    withLabel: 'some_proc_label' {
        cpus = 1
        memory = '1 GB'
        time = '1.1 h'
    }
    withLabel: 'another_label' {
        cpus = 2
        memory = '2 GB'
        time = '2.2 h'
        queue = 'customqueue'
    }
    withLabel: 'fourth_label' {
        cpus = 4
        time = '4.4 h'
        queue = 'anotherqueue'
    }
}
"""

INFRA_NFCORE_SINGULARITY_LOCAL_CONFIG = """\
params {
    config_profile_contact = 'my name (@myhandle)'
    config_profile_description = 'A cool description'
    config_profile_url = 'https://example.com'
    igenomes_base = '/data/igenomes/cache'
}
executor {
    queueSize = 200
    pollInterval = '15 s'
    submitRateLimit = '25 min'
}
process {
    resourceLimits = [cpus: 8, memory: '32 GB', time: '19.5 h']
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

INFRA_CUSTOM_SINGULARITY_LOCAL_CONFIG = """\
params {
    config_profile_description = 'A cool description'
}
executor {
    queueSize = 200
    pollInterval = '15 s'
    submitRateLimit = '25 min'
}
process {
    resourceLimits = [cpus: 8, memory: '32 GB', time: '19.5 h']
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
