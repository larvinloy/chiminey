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


import logging

from bdphpcprovider.corestages.stage import (
    Stage, get_url_with_pkey, copy_settings)

from bdphpcprovider import storage


logger = logging.getLogger(__name__)


class CopyDirectoryStage(Stage):
    """
    copies directories from one location to another
    """
    def __init__(self, user_settings=None):
        self.user_settings = user_settings.copy()
        self.boto_settings = user_settings.copy()
        pass

    def input_valid(self, settings_to_test):
        return (True, "ok")

    def triggered(self, run_settings):
        """
        Return true if the directory pattern triggers this stage, or there
        has been any other error
        """
        # FIXME: Need to verify that triggered is idempotent.
        logger.debug("CopyDirectory Stage Triggered?")
        logger.debug("run_settings=%s" % run_settings)

        if self._exists(run_settings, 'http://rmit.edu.au/schemas/stages/copy/testing', 'output'):
            self.val = run_settings['http://rmit.edu.au/schemas/stages/copy/testing']['output']
        else:
            self.val = 0

        dest_url = run_settings['http://rmit.edu.au/schemas/copy/files']['file1']
        logger.debug("dest_url=%s" % dest_url)

        copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/system/platform')

        dir_exists = False
        try:
            encoded_d_url = get_url_with_pkey(self.boto_settings, dest_url)
            dir_exists = storage.dir_exists(encoded_d_url)
            logger.debug("dir_exists=%s" % dir_exists)
        except IOError:
            # TODO: should check checksum of dest to make sure we have correct transfer
            logger.debug("dest file does not exist: %s" % dest_url)
            return True
        except Exception, e:
            logger.debug("dest file does not exist from exeception %s" % e)
            return True

        return not dir_exists

    def process(self, run_settings):
        """ perfrom the stage operation
        """
        logger.debug("CopyDirectory Stage Processing")
        logger.debug("run_settings=%s" % run_settings)
        logger.debug("boto_settings=%s", self.boto_settings)

        source_url = run_settings['http://rmit.edu.au/schemas/copy/files']['file0']
        logger.debug("source_url=%s" % source_url)
        encoded_s_url = get_url_with_pkey(self.boto_settings, source_url)

        dest_url = run_settings['http://rmit.edu.au/schemas/copy/files']['file1']
        logger.debug("dest_url=%s" % dest_url)
        encoded_d_url = get_url_with_pkey(self.boto_settings, dest_url)

        storage.copy_directories(encoded_s_url, encoded_d_url)

        # content = hrmcstages.get_file(encoded_s_url)  # we assume text files
        # logger.debug("content=%s" % content)
        # hrmcstages.put_file(encoded_d_url, content.encode('utf-8'))  # we assume text files

    def output(self, run_settings):
        """ produce the resulting datfiles and metadata
        """
        logger.debug("CopyDirectory Stage Output")
        logger.debug("run_settings=%s" % run_settings)

        if not self._exists(run_settings, 'http://rmit.edu.au/schemas/stages/copy/testing'):
            run_settings['http://rmit.edu.au/schemas/stages/copy/testing'] = {}

        self.val += 1
        run_settings['http://rmit.edu.au/schemas/stages/copy/testing']['output'] = self.val

        return run_settings


class CopyFileStage(Stage):

    """
    Moves file from one location to another
    """
    def __init__(self, user_settings=None):
        self.user_settings = user_settings.copy()
        self.boto_settings = user_settings.copy()
        pass

    def input_valid(self, settings_to_test):
        return (True, "ok")

    def triggered(self, run_settings):
        """
        Return true if the directory pattern triggers this stage, or there
        has been any other error
        """
        # FIXME: Need to verify that triggered is idempotent.
        logger.debug("Copy File Stage Triggered?")
        logger.debug("run_settings=%s" % run_settings)

        if self._exists(run_settings, 'http://rmit.edu.au/schemas/stages/copy/testing', 'output'):
            self.val = run_settings['http://rmit.edu.au/schemas/stages/copy/testing']['output']
        else:
            self.val = 0

        dest_url = run_settings['http://rmit.edu.au/schemas/copy/files']['file1']
        logger.debug("dest_url=%s" % dest_url)

        copy_settings(self.boto_settings, run_settings,
            'http://rmit.edu.au/schemas/system/platform')

        file_exists = False
        try:
            encoded_d_url = get_url_with_pkey(self.boto_settings, dest_url)
            file_exists = storage.file_exists(encoded_d_url)
            logger.debug("file_exists=%s" % file_exists)
        except IOError:
            # TODO: should check checksum of dest to make sure we have correct transfer
            logger.debug("dest file does not exist: %s" % dest_url)
            return True

        return not file_exists

    def process(self, run_settings):
        """ perfrom the stage operation
        """
        logger.debug("Copy File Stage Processing")
        logger.debug("run_settings=%s" % run_settings)
        logger.debug("boto_settings=%s", self.boto_settings)

        source_url = run_settings['http://rmit.edu.au/schemas/copy/files']['file0']
        logger.debug("source_url=%s" % source_url)
        encoded_s_url = get_url_with_pkey(self.boto_settings, source_url)

        dest_url = run_settings['http://rmit.edu.au/schemas/copy/files']['file1']
        logger.debug("dest_url=%s" % dest_url)
        encoded_d_url = get_url_with_pkey(self.boto_settings, dest_url)

        content = storage.get_file(encoded_s_url)  # we assume text files
        logger.debug("content=%s" % content)
        storage.put_file(encoded_d_url, content.encode('utf-8'))  # we assume text files

    def output(self, run_settings):
        """ produce the resulting datfiles and metadata
        """
        logger.debug("Copy File Stage Output")
        logger.debug("run_settings=%s" % run_settings)

        if not self._exists(run_settings, 'http://rmit.edu.au/schemas/stages/copy/testing'):
            run_settings['http://rmit.edu.au/schemas/stages/copy/testing'] = {}

        self.val += 1
        run_settings['http://rmit.edu.au/schemas/stages/copy/testing']['output'] = self.val

        return run_settings
