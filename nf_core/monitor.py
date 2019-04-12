#!/usr/bin/env python
"""Status monitor for nextflow pipelines.

Starts an OpenAPI server which handles weblog messages from nextflow.
"""

import os
import tempfile
import pickle
import logging

import connexion
from flask import g

from nf_core.openapi_server import encoder, db

def start_monitor(port=8080):
    """Starts the OpenAPI server with specified port """
    specification_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'openapi_server')
    logging.debug("Specification directory is at {}".format(specification_dir))
    app = connexion.App(__name__, specification_dir=os.path.join(specification_dir, './openapi/'))
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'nextflow monitor'},
                pythonic_params=True)

    with app.app.app_context(): # create a default temporary database
        db.get_db()

    @app.app.teardown_appcontext
    def close_db(e=None): # tears down g.db from application context
        database = g.pop('db', None)

        if database is not None:
            pickle.dump(database, open(os.path.join(tempfile.gettempdir(), 'nf_core.db'), 'wb'))
    
    app.run(port=port)
