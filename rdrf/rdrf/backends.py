from useraudit.backend import AuthFailedLoggerBackend
from useraudit.signals import login_failure_limit_reached

import logging
logger = logging.getLogger(__name__)

def account_lockout_handler(sender, user=None, **kwargs):
    from django.conf import settings
    logger.debug("account locked notification hit: sender %s kwargs %s" % (sender,
                                                                           kwargs))

    from rdrf.email_notification import process_notification
    from useraudit.middleware import get_request

    template_data = {
        "user": user,
    }

    registry_code = getattr(settings, "FALLBACK_REGISTRY_CODE", None)

    if registry_code:
        process_notification(registry_code,"account-locked",
                             get_request().LANGUAGE_CODE, template_data)
    else:
        logger.debug("No settings.FALLBACK_REGISTRY_CODE- no notifications sent")




login_failure_limit_reached.connect(account_lockout_handler)


