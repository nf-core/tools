import os
import pickle
import tempfile

from flask import g

def get_db():
    """ Returns a database for the current session """

    if 'db' not in g:
        temporaryDatabase = os.path.join(tempfile.gettempdir(), 'nf_core.db')
        # A temporary database under the /var directory
        if os.path.isfile(temporaryDatabase):
            g.db = pickle.load(open(temporaryDatabase, 'rb'))
        else:
            g.db = {}
            g.db['events'] = []
            g.db['runs'] = []

    return g.db
