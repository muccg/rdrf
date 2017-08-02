from rdrf.email_notification import process_notification

def process_reminder(user, registry_model):
    template_data = {"user": user,
                     "registry": registry_model}
    
    process_notification(registry_model.code,
                         "reminder",
                         template_data)
    
