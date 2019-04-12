from flask import abort

from nf_core.openapi_server.models.inline_response200 import InlineResponse200  # noqa: E501
from nf_core.openapi_server import db

def get_event(run_id, event):  # noqa: E501
    """Returns the trace of the specified event

     # noqa: E501

    :param run_id: 
    :type run_id: 
    :param event: The event to return for the run, e.g &#39;started&#39;
    :type event: str

    :rtype: object
    """
    database = db.get_db()
    event = [ev for ev in database if ev['runId'] == run_id and ev['event'] == event]
    if len(event):
        return event[0]
    else:
        abort(404)

def list_events(run_id):  # noqa: E501
    """Lists received events for a run

     # noqa: E501

    :param run_id: 
    :type run_id: 

    :rtype: List[InlineResponse200]
    """
    database = db.get_db()
    received_events = [InlineResponse200(event['event'], event['utcTime']) for event in database if event['runId'] == run_id]
    if len(received_events):
        return received_events
    else:
        abort(404)

def list_runs():  # noqa: E501
    """Lists available run names

     # noqa: E501


    :rtype: List[str]
    """

    database = db.get_db()
    return list(set([event['runId'] for event in database]))
