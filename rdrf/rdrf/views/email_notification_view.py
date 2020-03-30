import logging
import json

from django.views.generic.base import View
from django.shortcuts import redirect
from django.urls import reverse
from django.apps import apps
from django.contrib import messages
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from rdrf.services.io.notifications.email_notification import RdrfEmail
from rdrf.events.events import EventType
from rdrf.services.io.notifications.email_notification import EmailNotificationHistory


logger = logging.getLogger(__name__)


class ResendEmail(View):

    template_data = {}

    # TODO most of this code probably belongs on an EmailNotificationHistoryManager method
    # To be done as part of EmailNotificationHistory redesign #447
    @method_decorator(login_required)
    def get(self, request, notification_history_id):
        self.notification_history_id = notification_history_id
        history = EmailNotificationHistory.objects.get(pk=notification_history_id)
        self.template_data = history.template_data

        self._get_template_data()

        if EventType.is_registration(history.email_notification.description):
            self._ensure_registration_not_expired()

        email = RdrfEmail(
            language=history.language,
            email_notification=history.email_notification,
        )
        for key, value in self.template_data.items():
            email.append(key, value)
        email.send()

        messages.add_message(request, messages.SUCCESS, "Email resend")

        return redirect(reverse("admin:rdrf_emailnotificationhistory_changelist"))

    def _get_template_data(self):
        self.template_data = json.loads(self.template_data)
        for key, value in self.template_data.items():
            if isinstance(value, dict) and 'app' in value and 'model' in value:
                app = value.get("app")
                model = value.get("model")
                app_model = apps.get_model(app_label=app, model_name=model)
                self.template_data[key] = app_model.objects.get(id=value.get("id"))

    def _ensure_registration_not_expired(self):
        registration = self.template_data.get('registration')
        if registration is None:
            logger.warning(
                'Template data for notification history %s should contain "registration" object',
                self.notification_history_id)
            return
        user = registration.user
        if user.is_active:
            logger.info(f"User id {user.id} already active. Not changing anything.")
            return
        registration.activated = False
        user.date_joined = timezone.now()
        registration.save()
        user.save()
        logger.info(f"Changed date_joined of user id {user.id} to today.")
