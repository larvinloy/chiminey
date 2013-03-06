from bdphpcprovider.smartconnectorscheduler.smartconnector import Stage, UI
from bdphpcprovider.smartconnectorscheduler.filesystem import FileSystem, DataObject
from bdphpcprovider.smartconnectorscheduler.hrmcstages import get_settings
from bdphpcprovider.smartconnectorscheduler.errors import ContextKeyMissing

import logging
logger = logging.getLogger(__name__)


class Configure(Stage, UI):
    """
        - Creates file system,
        - Loads config.sys file into the filesystem,
        - Stores a reference to the filesystem in dictionary
    """
    def triggered(self, context):
        """
        True if filesystem does not exist in context
        """
        try:
            fsys = get_settings(context)
        except ContextKeyMissing:
            logger.debug("Configure triggered")
            return True
        else:
            logger.debug("Configure not triggered")
            return False

    def process(self, context):
        """
        Create global filesystem and then load config.sys to the filesystem
        """
        logger.debug("Process context %s" % context)
        global_filesystem = context['global_filesystem']
        local_filesystem = 'default'
        self.filesystem = FileSystem(global_filesystem, local_filesystem)

        original_config_file_path = context['config.sys']
        original_config_file = open(original_config_file_path, 'r')
        original_config_file_content = original_config_file.read()
        original_config_file.close()

        data_object = DataObject("config.sys")
        data_object.create(original_config_file_content)
        self.filesystem.create(local_filesystem, data_object)

    def output(self, context):
        """
        Store ref to new filesystem in context
        """

        context['filesys'] = self.filesystem
        logger.debug("output context %s" % context)
        return context
