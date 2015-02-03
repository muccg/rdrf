from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_app
import logging

logger = logging.getLogger("registry_log")


class Notifier(object):
    def __init__(self):
        self.enabled = self._check_installed()

    def _check_installed(self):
        try:
            app = get_app('notiifcation')
            return True
        except ImproperlyConfigured:
            return False

    def send(self, to_users, label, from_user, **kwargs):
        if not self.enabled:
            return
        from notification import models as notification
        notification.send(to_users, label, from_user, **kwargs)
        logger.debug("notification: %s sent from %s to %s with args %s" % (label, from_user,  to_users, kwargs))


