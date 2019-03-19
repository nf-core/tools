#!/usr/bin/env python
"""
nf-core monitor flask app
"""

import click
import flask

from nf_core.monitor import api, track

def create_nf_core_app():
    app = flask.Flask('nf_core.monitor.app')
    register_blueprints(app)
    return app

def register_blueprints(app):
    """
    Set up the blueprints for each website section
    """
    app.register_blueprint(api.views.api_blueprint)
    app.register_blueprint(track.views.track_blueprint)
    return None

# Default flask cli group. Gives run / routes / shell subcommands
@click.group(cls=flask.cli.FlaskGroup, create_app=create_nf_core_app)
def monitor():
    """
    Run the nf-core monitor flask app
    """
