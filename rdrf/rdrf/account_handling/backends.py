from useraudit.signals import login_failure_limit_reached

from rdrf.events.events import EventType

import logging
logger = logging.getLogger(__name__)


def account_lockout_handler(sender, user=None, **kwargs):
    from rdrf.services.io.notifications.email_notification import process_notification

    template_data = {
        "user": user,
    }

    for registry_model in user.registry.all():
        process_notification(registry_model.code, EventType.ACCOUNT_LOCKED, template_data)


login_failure_limit_reached.connect(account_lockout_handler)
