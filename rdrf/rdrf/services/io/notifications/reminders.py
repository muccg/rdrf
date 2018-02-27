from rdrf.services.io.notifications.email_notification import process_notification
from rdrf.services.io.notifications.email_notification import EmailNotificationHistory
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ReminderProcessor:
    def __init__(self, user, registry_model, process_func=process_notification):
        self.user = user
        self.registry_model = registry_model
        self.registry_id = registry_model.id
        self.user_id = user.id
        self.threshold = self.user.last_login
        self.process_func = process_func  # exposed to allow testing

    def _can_send(self):
        # These are the rules for MTM - should we push into config?
        now = datetime.now()
        existing_reminders = self._get_reminders()
        num_sent = len(existing_reminders)
        if num_sent >= 2:
            return False
        elif num_sent == 1:
            last_reminder = existing_reminders[-1]
            delta = now - last_reminder.date_stamp
            return delta.days >= 14
        else:
            return True

    def _get_reminders(self):
        # own reminders since last login date
        history = EmailNotificationHistory.objects.filter(
            email_notification__description='reminder',
            date_stamp__gte=self.user.last_login)
        history = history.order_by("-date_stamp")
        return [enh for enh in history if self._is_own(enh)]

    def _is_own(self, email_notification_model):
        template_data = json.loads(email_notification_model.template_data)
        if not template_data:
            return False
        try:
            user_id = template_data["user"]["id"]
            registry_id = template_data["registry"]["id"]
            return registry_id == self.registry_id and user_id == self.user_id
        except KeyError:
            return False

    def process(self):
        if self._can_send():
            template_data = {"user": self.user,
                             "registry": self.registry_model}

            self.process_func(self.registry_model.code,
                              "reminder",
                              template_data)
            return True
