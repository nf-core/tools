#!/usr/bin/env python
"""
nf-core monitor - tracking commands
"""

import flask
app = flask.Flask('nf_core.monitor.app')

track_blueprint = flask.Blueprint('track', __name__)

# Routes - match URL destinations to functions
@track_blueprint.route('/')
def dashboard():
    return flask.render_template('track/dashboard.html')
