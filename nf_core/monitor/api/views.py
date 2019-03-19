#!/usr/bin/env python
"""
nf-core monitor - api commands
"""

import flask
app = flask.Flask('nf_core.monitor.app')

api_blueprint = flask.Blueprint('api', __name__)

# Routes - match URL destinations to functions
@api_blueprint.route('/api/')
def api_root():
    return flask.jsonify({
        'message': 'Welcome to the nf-core monitor REST API',
        'api_routes': {
            '/api/test/': 'Get a test API response'
        }
    })

@api_blueprint.route('/api/test')
def test():
    return flask.jsonify({
        'success': True,
        'name': 'fubar',
        'message': 'Test API call successful'
    })
