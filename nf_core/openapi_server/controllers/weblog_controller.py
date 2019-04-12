from flask import request

from nf_core.openapi_server import db

def submit_event(body=None):  # noqa: E501
    """Receives events from nextflows weblog

     # noqa: E501

    :param body: An event json object
    :type body: 

    :rtype: None
    """

    event = request.get_json()
    database = db.get_db()
    if event['runId'] not in database['runs']:
         database['runs'].append(event['runId'])
     
    database['events'] = event
    return "Added event successfully."
