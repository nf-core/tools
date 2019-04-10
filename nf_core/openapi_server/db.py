from flask import current_app, g

def get_db():
    """ Returns a database for the current session """

    if 'db' not in g:
        g.db = {}
        g.db['events'] = []
        g.db['runs'] = []

    return g.db
