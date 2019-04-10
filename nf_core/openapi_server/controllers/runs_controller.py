import connexion
import six

from nf_core.openapi_server.models.inline_response200 import InlineResponse200  # noqa: E501
from nf_core.openapi_server import util


def get_event(run_id, event):  # noqa: E501
    """Returns the trace of the specified event

     # noqa: E501

    :param run_id: 
    :type run_id: 
    :param event: The event to return for the run, e.g &#39;started&#39;
    :type event: str

    :rtype: object
    """
    return 'do some magic!'


def list_events(run_id):  # noqa: E501
    """Lists received events for a run

     # noqa: E501

    :param run_id: 
    :type run_id: 

    :rtype: List[InlineResponse200]
    """
    return 'do some magic!'


def list_runs():  # noqa: E501
    """Lists available run names

     # noqa: E501


    :rtype: List[str]
    """
    return 'do some magic!'
