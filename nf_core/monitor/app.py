#!/usr/bin/env python
"""
nf-core monitor flask app
"""

import click
import flask

from nf_core.monitor import api, track

def register_blueprints(app):
    """
    Set up the blueprints for each website section
    """
    app.register_blueprint(api.views.api_blueprint)
    app.register_blueprint(track.views.track_blueprint)
    return None

# Default flask cli group. Gives run / routes / shell subcommands
@click.group(cls=flask.cli.FlaskGroup)
def monitor():
    """
    Run the nf-core monitor flask app
    """

app = flask.Flask(__name__)
register_blueprints(app)
