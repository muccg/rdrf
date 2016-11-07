import logging
import json

from django.views.generic.base import View
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.apps import apps
from django.contrib import messages

from .models import EmailNotificationHistory

from .email_notification import RdrfEmail

logger = logging.getLogger(__name__)


class ResendEmail(View):

    template_data = {}

    def get(self, request, notification_history_id):
        history = EmailNotificationHistory.objects.get(pk=notification_history_id)
        self.template_data = history.template_data

        self._get_template_data()

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
            app = value.get("app")
            model = value.get("model")
            app_model = apps.get_model(app_label=app, model_name=model)
            self.template_data[key] = app_model.objects.get(id=value.get("id"))
