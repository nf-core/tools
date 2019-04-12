#!/usr/bin/env python
"""Status monitor for nextflow pipelines.

Starts an OpenAPI server which handles weblog messages from nextflow.
"""

import os
import logging

import connexion

from nf_core.openapi_server import encoder

def start_monitor(port=8080):
    """Starts the OpenAPI server with specified port """
    specification_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'openapi_server')
    logging.debug("Specification directory is at {}".format(specification_dir))
    app = connexion.App(__name__, specification_dir=os.path.join(specification_dir, './openapi/'))
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'nextflow monitor'},
                pythonic_params=True)
    app.run(port=port)
