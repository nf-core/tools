# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from openapi_server.models.inline_response200 import InlineResponse200  # noqa: E501
from openapi_server.test import BaseTestCase


class TestRunsController(BaseTestCase):
    """RunsController integration test stubs"""

    def test_get_event(self):
        """Test case for get_event

        Returns the trace of the specified event
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/run/{run_id}/{event}'.format(run_id='run_id_example', event='event_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_list_events(self):
        """Test case for list_events

        Lists received events for a run
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/events/{run_id}'.format(run_id='run_id_example'),
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_list_runs(self):
        """Test case for list_runs

        Lists available run names
        """
        headers = { 
            'Accept': 'application/json',
        }
        response = self.client.open(
            '/runs',
            method='GET',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
