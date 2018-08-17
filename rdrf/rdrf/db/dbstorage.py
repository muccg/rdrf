from storages.backends.database import DatabaseStorage
from django.utils.deconstruct import deconstructible
import logging
import os
from django.utils.crypto import get_random_string
from django.core.exceptions import SuspiciousFileOperation

logger = logging.getLogger(__name__)


@deconstructible
class DatabaseStorage(DatabaseStorage): 
    # Disabled 'Blob overwritten' behaviour from storages.backends.database
    # Now will append random string to filename when file already exist in rdrf_filestorage db
    def get_available_name(self, name, max_length=None):
        file_root, file_ext = os.path.splitext(name)
        while self.exists(name) or (max_length and len(name) > max_length):
            # file_ext includes the dot.
            name = "".join("%s_%s%s" % (file_root, get_random_string(7), file_ext))
            if max_length is None:
                continue
            # Truncate file_root if max_length exceeded.
            truncation = len(name) - max_length
            if truncation > 0:
                file_root = file_root[:-truncation]
                # Entire file_root was truncated in attempt to find an available filename.
                if not file_root:
                    raise SuspiciousFileOperation(
                        'Storage can not find an available filename for "%s". '
                        'Please make sure that the corresponding file field '
                        'allows sufficient "max_length".' % name
                    )
                name = "".join("%s_%s%s" % (file_root, get_random_string(7), file_ext))
        return name
