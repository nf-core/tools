#!/usr/bin/env python
""" Release code for the nf-core python package.

Bumps the version number in all appropriate files for
a nf-core pipeline
"""

import logging
import os
import re

def make_release(lint_obj, new_version):
    """ Function to make the release. Called by the main script """

    # Collect the old and new version numbers
    current_version = lint_obj.config['manifest.pipelineVersion'].strip(' \'"')
    if new_version.startswith('v'):
        logging.warn("Stripping leading 'v' from new version number")
        new_version = new_version[1:]
    logging.info("Changing version number:\n  Current version number is '{}'\n  New version number will be '{}'".format(current_version, new_version))

    # Update nextflow.config
    nfconfig_pattern = r"pipelineVersion\s*=\s*[\'\"]?{}[\'\"]?".format(current_version.replace('.','\.'))
    nfconfig_newstr = "pipelineVersion = '{}'".format(new_version)
    update_file_version("nextflow.config", lint_obj, nfconfig_pattern, nfconfig_newstr)

    # Update container tag
    docker_tag = 'latest'
    if new_version.replace('.', '').isdigit():
        docker_tag = new_version
    else:
        logging.info("New version contains letters. Setting docker tag to 'latest'")
    nfconfig_pattern = r"container\s*=\s*[\'\"]nfcore/{}:(?:{}|latest)[\'\"]".format(lint_obj.pipeline_name.lower(), current_version.replace('.','\.'))
    nfconfig_newstr = "container = 'nfcore/{}:{}'".format(lint_obj.pipeline_name.lower(), docker_tag)
    update_file_version("nextflow.config", lint_obj, nfconfig_pattern, nfconfig_newstr)

    # Update travis image tag
    nfconfig_pattern = r"docker tag nfcore/{name} nfcore/{name}:(?:{tag}|latest)".format(name=lint_obj.pipeline_name.lower(), tag=current_version.replace('.','\.'))
    nfconfig_newstr = "docker tag nfcore/{name} nfcore/{name}:{tag}".format(name=lint_obj.pipeline_name.lower(), tag=docker_tag)
    update_file_version(".travis.yml", lint_obj, nfconfig_pattern, nfconfig_newstr)

    # Update Singularity version name
    nfconfig_pattern = r"VERSION {}".format(current_version.replace('.','\.'))
    nfconfig_newstr = "VERSION {}".format(new_version)
    update_file_version("Singularity", lint_obj, nfconfig_pattern, nfconfig_newstr)

    if 'environment.yml' in lint_obj.files:
        # Update conda environment.yml
        nfconfig_pattern = r"name: nf-core-{}-{}".format(lint_obj.pipeline_name.lower(), current_version.replace('.','\.'))
        nfconfig_newstr = "name: nf-core-{}-{}".format(lint_obj.pipeline_name.lower(), new_version)
        update_file_version("environment.yml", lint_obj, nfconfig_pattern, nfconfig_newstr)

def update_file_version(filename, lint_obj, pattern, newstr):
    """ Update manifest.pipelineVersion in the nextflow config file """

    # Load the file
    fn = os.path.join(lint_obj.path, filename)
    content = ''
    with open(fn, 'r') as fh:
        content = fh.read()

    # Check that we have exactly one match
    matches = re.findall(pattern, content)
    if len(matches) == 0:
        raise SyntaxError ("Could not find version number in {}: '{}'".format(filename, pattern))
    if len(matches) > 1:
        raise SyntaxError ("Found more than one version number in {}: '{}'".format(filename, pattern))

    # Replace the match
    logging.info("Updating version in {}\n - {}\n + {}".format(filename, matches[0], newstr))
    new_content = re.sub(pattern, newstr, content)
    with open(fn, 'w') as fh:
        fh.write(new_content)
