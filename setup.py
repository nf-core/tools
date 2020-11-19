#!/usr/bin/env python

from setuptools import setup, find_packages
import sys

version = "1.12"

with open("README.md") as f:
    readme = f.read()

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
    entry_points={"console_scripts": ["nf-core=nf_core.__main__:run_nf_core"]},
    install_requires=[
        "cookiecutter",
        "click",
        "GitPython",
        "jinja2",
        "jsonschema",
        "PyInquirer==1.0.2",
        "pyyaml",
        "requests",
        "requests_cache",
        "rich>=9",
        "tabulate",
    ],
    setup_requires=["twine>=1.11.0", "setuptools>=38.6."],
    packages=find_packages(exclude=("docs")),
    include_package_data=True,
    zip_safe=False,
)
