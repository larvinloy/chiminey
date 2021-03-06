__author__ = 'iman'

# Copyright (C) 2016, RMIT University

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


from django.core.management.base import BaseCommand
from django.conf import settings as django_settings
from chiminey.smartconnectorscheduler import jobs
from  distutils.dir_util  import copy_tree
import os


class Command(BaseCommand):
    """
    Load up the initial state of the database (replaces use of
    fixtures).  Assumes specific structure.
    """
    args = ''
    help = 'Setup an initial task structure.'
    def setup(self, initialiser, name, description):
        MESSAGE = "This will delete %s smart connector.  Are you sure [Yes/No]?" % name
        confirm = raw_input(MESSAGE)
        if confirm != "Yes":
            print "action aborted by user"
            return
        directive = jobs.safe_import(initialiser, [], {})
        directive.delete_directive(name)
        print "done"


    def handle(self, *args, **options):
            current_sm = django_settings.SMART_CONNECTORS[args[0]]
            print current_sm['init'], current_sm['name'], current_sm['description']
            if current_sm['payload']:
                destination = os.path.join(django_settings.PAYLOAD_DESTINATION, os.path.basename(current_sm['payload']))
                print destination
                print django_settings.PAYLOAD_DESTINATION
                copy_tree(current_sm['payload'],
                         destination)
            self.setup(current_sm['init'], current_sm['name'], current_sm['description'])
            print "done"


