#!/usr/bin/env python

from setuptools import find_packages, setup

version = "2.14.0"

with open("README.md") as f:
    readme = f.read()

with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="nf-core",
    version=version,
    description="Helper tools for use with nf-core Nextflow pipelines.",
    long_description=readme,
    long_description_content_type="text/markdown",
    keywords=[
        "nf-core",
        "nextflow",
        "bioinformatics",
        "workflow",
        "pipeline",
        "biology",
        "sequencing",
        "NGS",
        "next generation sequencing",
    ],
    author="Phil Ewels",
    author_email="phil.ewels@scilifelab.se",
    url="https://github.com/nf-core/tools",
    license="MIT",
    entry_points={
        "console_scripts": ["nf-core=nf_core.__main__:run_nf_core"],
        "refgenie.hooks.post_update": ["nf-core-refgenie=nf_core.refgenie:update_config"],
    },
    python_requires=">=3.8, <4",
    install_requires=required,
    packages=find_packages(exclude=("docs")),
    include_package_data=True,
    zip_safe=False,
)
