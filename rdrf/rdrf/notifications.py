from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_app
import logging
from rdrf.utils import get_user, get_users


logger = logging.getLogger("registry_log")


class Notifier(object):

    def send(self, to_users, label, from_user, **kwargs):
        from notification import models as nf
        logger.debug("Trying to send notication from user %s to %s notification type %s with data %s" % (from_user, to_users, label, kwargs))
        nf.send(to_users, label, [from_user], **kwargs)
        logger.debug("notification: %s sent from %s to %s with args %s" % (label, from_user, to_users, kwargs))