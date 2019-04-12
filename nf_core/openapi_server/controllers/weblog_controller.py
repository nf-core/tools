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
    database.append(event)
    return "Added event successfully."
