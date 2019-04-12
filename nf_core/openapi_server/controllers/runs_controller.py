from werkzeug.wrappers import BaseResponse as Response

from nf_core.openapi_server.models.inline_response200 import InlineResponse200  # noqa: E501
from nf_core.openapi_server import util, db

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
    if run_id not in database['runs']:
         return Response('Run with run id {} not found'.format(run_id))
    return [ev for ev in database if ev['runId'] == run_id and ev['event'] == event]


def list_events(run_id):  # noqa: E501
    """Lists received events for a run

     # noqa: E501

    :param run_id: 
    :type run_id: 

    :rtype: List[InlineResponse200]
    """
    database = db.get_db()
    if run_id not in database['runs']:
        return Response('Run with run id {} not found'.format(run_id))
    return [InlineResponse200(event=event['event'], utc_time=event['utcTime']) for event in database['events'] if event['runId'] == run_id]

def list_runs():  # noqa: E501
    """Lists available run names

     # noqa: E501


    :rtype: List[str]
    """

    database = db.get_db()
    return database['runs']
