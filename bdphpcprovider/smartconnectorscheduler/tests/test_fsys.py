# Copyright (C) 2013, RMIT University

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import os
import tempfile
import unittest
import logging
import logging.config

from django.contrib.auth.models import User
from django import test as djangotest
from bdphpcprovider.smartconnectorscheduler.management.commands import view
from bdphpcprovider.smartconnectorscheduler import models
from bdphpcprovider.smartconnectorscheduler import hrmcstages
from bdphpcprovider.smartconnectorscheduler import smartconnector

from bdphpcprovider.smartconnectorscheduler.stages.errors import BadInputException
logger = logging.getLogger(__name__)

def error(e):
    raise


class TestBDPURLS(unittest.TestCase):
    """
    Test functions that manipulate BDPURLS>
    """

    def setUp(self):
        pass


    def tearDown(self):
        pass

    def test_get_url_with_key(self):

        models.Platform.objects.get_or_create(name='nci',
            root_path="/var/cloudenabling/nci")
        models.Platform.objects.get_or_create(name='local',
            root_path="/var/cloudenabling/remotesys")


        settings = {
            'nci_private_key':'nci_private_key',
            'nci_user': 'nci_user',
            'nci_password': 'nci_password'
        }
        url = "ssh://nci@127.0.0.1/remote/greet.txt"

        res = smartconnector.get_url_with_pkey(settings, url)

        self.assertEquals("ssh://127.0.0.1/remote/greet.txt?"
            "key_file=nci_private_key&password=nci_password&"
            "root_path=/var/cloudenabling/nci&username=nci_user", res)

        url = "ssh://127.0.0.1/foo/bar.txt"

        res = smartconnector.get_url_with_pkey(settings, url)

        self.assertEquals("file://127.0.0.1/foo/bar.txt?"
            "root_path=/var/cloudenabling/remotesys", res)


        url = 'file://local@127.0.0.1/local/finalresult.txt'

        res = smartconnector.get_url_with_pkey(settings, url)

        self.assertEquals("file://127.0.0.1/local/finalresult.txt?"
            "root_path=/var/cloudenabling/remotesys", res)

        url = 'file://local@127.0.0.1/local/finalresult.txt'

        res = smartconnector.get_url_with_pkey(settings, url)

        self.assertEquals("file://127.0.0.1/local/finalresult.txt?root_path=/var/cloudenabling/remotesys", res)

        url = 'file://127.0.0.1/hrmcrun/input_0'

        res = smartconnector.get_url_with_pkey(settings, url)

        self.assertEquals("file://127.0.0.1/hrmcrun/input_0?root_path=/var/cloudenabling/remotesys", res)

        url = 'celery_payload_2'

        res = smartconnector.get_url_with_pkey(settings, url, is_relative_path=True)

        self.assertEquals("file://127.0.0.1/celery_payload_2/?root_path=/var/cloudenabling/remotesys", res)

        url = 'nci@celery_payload_2'

        res = smartconnector.get_url_with_pkey(settings, url, is_relative_path=True)

        self.assertEquals("ssh://127.0.0.1/celery_payload_2/?key_file=nci_private_key&password=nci_password&root_path=/var/cloudenabling/nci&username=nci_user", res)




