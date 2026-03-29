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
