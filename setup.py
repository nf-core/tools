#!/usr/bin/env python

from setuptools import setup, find_packages

version = '1.0'

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name = 'nf-core',
    version = version,
    description = 'Helper tools for use with nf-core Nextflow pipelines.',
    long_description = readme,
    keywords = ['nf-core', 'nextflow', 'bioinformatics', 'workflow', 'pipeline', 'biology', 'sequencing', 'NGS', 'next generation sequencing'],
    author = 'Phil Ewels',
    author_email = 'phil.ewels@scilifelab.se',
    url = 'https://github.com/nf-core/tools',
    license = license,
    scripts = ['scripts/nf-core'],
    install_requires = [
        'click',
        'GitPython',
        'pyyaml',
        'requests',
        'requests_cache',
        'tabulate'
    ],
    packages = find_packages(exclude=('docs')),
    include_package_data = True,
    zip_safe = False
)
