#!/usr/bin/env python
"""
Update a nextflow.config file with refgenie genomes
"""

import logging
import os
import re
import refgenconf
from warnings import warn

log = logging.getLogger(__name__)

NF_CFG_TEMPLATE = """
params {{
  genomes {{
{content}
  }}
}}
"""


def print_nf_config(rgc):
    """
    Generate a nextflow config file with the genomes
    from the refgenie config file
    Adapted from: https://github.com/refgenie/refgenie_nfcore

    Takes a RefGenConf object as argument
    """
    abg = rgc.list_assets_by_genome()
    genomes_str = ""
    for genome, asset_list in abg.items():
        genomes_str += "    '{}' {{\n".format(genome)
        for asset in asset_list:
            try:
                pth = rgc.seek(genome, asset)
            except refgenconf.exceptions.MissingSeekKeyError:
                log.warn(f"{genome}/{asset} is incomplete, ignoring...")
            else:
                genomes_str += '      {} = "{}"\n'.format(asset.ljust(20, " "), pth)

    return NF_CFG_TEMPLATE.format(content=genomes_str)


def update_nextflow_home_config(refgenie_genomes_config_file, nxf_home):
    # Check if NXF_HOME/config exists and has a
    include_config_string = f"includeConfig '{os.path.abspath(refgenie_genomes_config_file)}'\n"
    nxf_home_config = os.path.join(nxf_home, "config")
    if os.path.exists(nxf_home_config):
        # look for include statement in config
        has_include_statement = False
        with open(nxf_home_config, "r") as fh:
            lines = fh.readlines()
            for line in lines:
                if re.match(f"\s*includeConfig\s*'{os.path.abspath(refgenie_genomes_config_file)}'", line):
                    has_include_statement = True
                    break

        # if include statement is missing, add it to the last line
        if not has_include_statement:
            with open(nxf_home_config, "a") as fh:
                fh.write(include_config_string)

            log.info(f"Included refgenie_genomes.config to {nxf_home_config}")

    else:
        # create new config and add include statement
        with open(nxf_home_config, "w") as fh:
            fh.write(include_config_string)
            log.info(f"Created new nextflow config file: {nxf_home_config}")


def update_config(rgc):
    """
    Update the genomes.config file after a local refgenie database has been updated
    """

    # Compile nextflow refgenie_genomes.config from refgenie config
    refgenie_genomes = print_nf_config(rgc)

    # Get the path to NXF_HOME
    # If NXF_HOME is not set, create it at $HOME/.nextflow
    # If $HOME is not set, set nxf_home to false
    nxf_home = os.environ.get("NXF_HOME")
    if not nxf_home and "HOME" in os.environ:
        nxf_home = os.path.join(os.environ.get("HOME"), ".nextflow")
        if not os.path.exists(nxf_home):
            os.makedirs(nxf_home, exist_ok=True)

    # Get the path for storing the updated refgenie_genomes.config
    if hasattr(rgc, "nextflow_config"):
        refgenie_genomes_config_file = rgc.nextflow_config
    elif "NXF_REFGENIE_PATH" in os.environ:
        refgenie_genomes_config_file = os.environ.get("NXF_REFGENIE_PATH")
    elif nxf_home:
        refgenie_genomes_config_file = os.path.join(nxf_home, "nf-core/refgenie_genomes.config")
    else:
        log.info("Could not determine path to 'refgenie_genomes.config' file.")
        return 

    # Save the udated genome config
    try:
        with open(refgenie_genomes_config_file, "w") as fh:
            fh.write(refgenie_genomes)
        log.info(f"Updated nf-core genomes config: {refgenie_genomes_config_file}")
    except FileNotFoundError as e:
        log.warn(f"Could not write to {refgenie_genomes_config_file}")

    # Add include statement to NXF_HOME/config
    if nxf_home:
        update_nextflow_home_config(refgenie_genomes_config_file, nxf_home)
