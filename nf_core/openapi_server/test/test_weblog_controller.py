# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from nf_core.openapi_server.test import BaseTestCase


class TestWeblogController(BaseTestCase):
    """WeblogController integration test stubs"""

    def test_submit_event(self):
        """Test case for submit_event

        Receives events from nextflows weblog
        """
        headers = { 
        }
        response = self.client.open(
            '/event',
            method='POST',
            headers=headers)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
