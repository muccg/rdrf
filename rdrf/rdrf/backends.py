from useraudit.backend import AuthFailedLoggerBackend
from django.conf import settings


class AuthFailedLoggerNotificationBackend(AuthFailedLoggerBackend):

    def notification(self):
        super(AuthFailedLoggerBackend, self).notification()
        from rdrf.email_notification import process_notification
        from useraudit.middleware import get_request

        template_data = {
            "user": self._get_user()
        }

        if self.registry_code:
            process_notification(self.registry_code, settings.EMAIL_NOTE_ACCOUNT_LOCKED,
                                 get_request().LANGUAGE_CODE, template_data)

    @property
    def registry_code(self):
        return getattr(settings, "FALLBACK_REGISTRY_CODE", None)
