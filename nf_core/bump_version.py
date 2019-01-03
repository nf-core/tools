#!/usr/bin/env python
""" Release code for the nf-core python package.

Bumps the version number in all appropriate files for
a nf-core pipeline
"""

import logging
import os
import re
import sys

def bump_pipeline_version(lint_obj, new_version):
    """ Function to bump a pipeline version number. Called by the main script """

    # Collect the old and new version numbers
    current_version = lint_obj.config.get('manifest.version', '').strip(' \'"')
    if new_version.startswith('v'):
        logging.warn("Stripping leading 'v' from new version number")
        new_version = new_version[1:]
    if not current_version:
        logging.error("Could not find config variable manifest.version")
        sys.exit(1)
    logging.info("Changing version number:\n  Current version number is '{}'\n  New version number will be '{}'".format(current_version, new_version))

    # Update nextflow.config
    nfconfig_pattern = r"version\s*=\s*[\'\"]?{}[\'\"]?".format(current_version.replace('.',r'\.'))
    nfconfig_newstr = "version = '{}'".format(new_version)
    update_file_version("nextflow.config", lint_obj, nfconfig_pattern, nfconfig_newstr)

    # Update container tag
    docker_tag = 'latest'
    if new_version.replace('.', '').isdigit():
        docker_tag = new_version
    else:
        logging.info("New version contains letters. Setting docker tag to 'latest'")
    nfconfig_pattern = r"container\s*=\s*[\'\"]nfcore/{}:(?:{}|latest)[\'\"]".format(lint_obj.pipeline_name.lower(), current_version.replace('.',r'\.'))
    nfconfig_newstr = "container = 'nfcore/{}:{}'".format(lint_obj.pipeline_name.lower(), docker_tag)
    update_file_version("nextflow.config", lint_obj, nfconfig_pattern, nfconfig_newstr)

    # Update travis image tag
    nfconfig_pattern = r"docker tag nfcore/{name}:dev nfcore/{name}:(?:{tag}|latest)".format(name=lint_obj.pipeline_name.lower(), tag=current_version.replace('.',r'\.'))
    nfconfig_newstr = "docker tag nfcore/{name}:dev nfcore/{name}:{tag}".format(name=lint_obj.pipeline_name.lower(), tag=docker_tag)
    update_file_version(".travis.yml", lint_obj, nfconfig_pattern, nfconfig_newstr)

    # Update Singularity version name
    nfconfig_pattern = r"VERSION {}".format(current_version.replace('.',r'\.'))
    nfconfig_newstr = "VERSION {}".format(new_version)
    update_file_version("Singularity", lint_obj, nfconfig_pattern, nfconfig_newstr)

    if 'environment.yml' in lint_obj.files:
        # Update conda environment.yml
        nfconfig_pattern = r"name: nf-core-{}-{}".format(lint_obj.pipeline_name.lower(), current_version.replace('.',r'\.'))
        nfconfig_newstr = "name: nf-core-{}-{}".format(lint_obj.pipeline_name.lower(), new_version)
        update_file_version("environment.yml", lint_obj, nfconfig_pattern, nfconfig_newstr)

        # Update Dockerfile PATH
        nfconfig_pattern = r"PATH\s+/opt/conda/envs/nf-core-{}-{}/bin:\$PATH".format(lint_obj.pipeline_name.lower(), current_version.replace('.',r'\.'))
        nfconfig_newstr = "PATH /opt/conda/envs/nf-core-{}-{}/bin:$PATH".format(lint_obj.pipeline_name.lower(), new_version)
        update_file_version("Dockerfile", lint_obj, nfconfig_pattern, nfconfig_newstr)

        # Update Singularity PATH
        nfconfig_pattern = r"PATH=/opt/conda/envs/nf-core-{}-{}/bin:\$PATH".format(lint_obj.pipeline_name.lower(), current_version.replace('.',r'\.'))
        nfconfig_newstr = "PATH=/opt/conda/envs/nf-core-{}-{}/bin:$PATH".format(lint_obj.pipeline_name.lower(), new_version)
        update_file_version("Singularity", lint_obj, nfconfig_pattern, nfconfig_newstr)

def bump_nextflow_version(lint_obj, new_version):
    """ Function to bump the required nextflow version number."""

    # Collect the old and new version numbers
    current_version = lint_obj.config.get('manifest.nextflowVersion', '').strip(' \'"')
    current_version = re.sub(r'[^0-9\.]', '', current_version)
    new_version = re.sub(r'[^0-9\.]', '', new_version)
    if not current_version:
        logging.error("Could not find config variable manifest.nextflowVersion")
        sys.exit(1)
    logging.info("Changing version number:\n  Current version number is '{}'\n  New version number will be '{}'".format(current_version, new_version))

    # Update nextflow.config
    nfconfig_pattern = r"nextflowVersion\s*=\s*[\'\"]?>={}[\'\"]?".format(current_version.replace('.',r'\.'))
    nfconfig_newstr = "nextflowVersion = '>={}'".format(new_version)
    update_file_version("nextflow.config", lint_obj, nfconfig_pattern, nfconfig_newstr)

    # Update travis config
    nfconfig_pattern = r"NXF_VER=[\'\"]?{}[\'\"]?".format(current_version.replace('.',r'\.'))
    nfconfig_newstr = "NXF_VER='{}'".format(new_version)
    update_file_version(".travis.yml", lint_obj, nfconfig_pattern, nfconfig_newstr, True)

    # Update README badge
    nfconfig_pattern = r"nextflow-%E2%89%A5{}-brightgreen.svg".format(current_version.replace('.',r'\.'))
    nfconfig_newstr = "nextflow-%E2%89%A5{}-brightgreen.svg".format(new_version)
    update_file_version("README.md", lint_obj, nfconfig_pattern, nfconfig_newstr, True)

def update_file_version(filename, lint_obj, pattern, newstr, allow_multiple=False):
    """ Update version number in the requested file """

    # Load the file
    fn = os.path.join(lint_obj.path, filename)
    content = ''
    with open(fn, 'r') as fh:
        content = fh.read()

    # Check that we have exactly one match
    matches = re.findall(pattern, content)
    if len(matches) == 0:
        raise SyntaxError ("Could not find version number in {}: '{}'".format(filename, pattern))
    if len(matches) > 1 and not allow_multiple:
        raise SyntaxError ("Found more than one version number in {}: '{}'".format(filename, pattern))

    # Replace the match
    logging.info("Updating version in {}\n - {}\n + {}".format(filename, matches[0], newstr))
    new_content = re.sub(pattern, newstr, content)
    with open(fn, 'w') as fh:
        fh.write(new_content)
