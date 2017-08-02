from rdrf.email_notification import process_notification

class Reminder:
    def __init__(self, user, registry_model):
        self.registry_model = registry_model
        self.user = user

    def _can_send(self):
        pass

    def send(self):
        if self._can_send():
            template_data = {"user": self.user,
                             "registry": self.registry_model}
    
            process_notification(self.registry_model.code,
                                 "reminder",
                                 template_data)
    
