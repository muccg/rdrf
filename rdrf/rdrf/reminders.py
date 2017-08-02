from rdrf.email_notification import process_notification
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ReminderProcessor:
    def __init__(self, user, registry_model):
        self.registry_model = registry_model
        self.user = user

    def _can_send(self):
        # These are the rules for MTM - should we push into config?
        now = datetime.now()
        existing_reminders = self._get_reminders()
        num_sent = len(existing_reminders)
        if num_sent >= 2:
            return False
        elif num_sent == 1:
            last_reminder = existing_reminders[-1]
            delta = now - last_reminder.date
            return  delta.days >= 14
        else:
            return True

    def _get_reminders(self):
        # to do - look at email notification history
        return []
        

    def process(self):
        if self._can_send():
            template_data = {"user": self.user,
                             "registry": self.registry_model}
    
            process_notification(self.registry_model.code,
                                 "reminder",
                                 template_data)
    
