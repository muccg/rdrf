from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
from django.views.generic.base import View
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _, ungettext

from useraudit.password_expiry import should_warn_about_password_expiry, days_to_password_expiry

from rdrf.services.io.notifications.email_notification import process_notification
from rdrf.events.events import EventType
from rdrf.workflows.verification import verifications_apply
from django.conf import settings
from django.http import Http404


# todo update ophg registries to use new demographics and patients listing
# forms: we need to fix this properly
def in_fkrp(user):
    user_reg_codes = [r.code for r in user.registry.all()]
    return "fkrp" in user_reg_codes


_ADMIN_PATIENT_LISTING = "admin:patients_patient_changelist"
_HOME_PAGE = "admin:index"
_PATIENTS_LISTING = "patientslisting"


class RouterView(View):

    def get(self, request):
        user = request.user

        redirect_url = None

        if user.is_authenticated:
            if settings.PROMS_SITE:
                if user.is_superuser:
                    redirect_url = reverse(_HOME_PAGE)
                else:
                    raise Http404()
            elif user.is_superuser:
                redirect_url = reverse(_PATIENTS_LISTING)
            elif user.is_clinician and user.my_registry and verifications_apply(user):
                redirect_url = reverse("verifications_list", args=[user.registry_code])
            elif user.is_clinician:
                redirect_url = reverse(_PATIENTS_LISTING)
            elif user.is_genetic_staff:
                redirect_url = reverse(_PATIENTS_LISTING)
            elif user.is_working_group_staff:
                redirect_url = reverse(_PATIENTS_LISTING)
            elif user.is_genetic_curator:
                redirect_url = reverse(_PATIENTS_LISTING)
            elif user.is_curator:
                redirect_url = reverse(_PATIENTS_LISTING)
            elif user.is_parent or user.is_patient or user.is_carrier:
                if user.num_registries == 1:
                    registry_code = user.get_registries()[0].code
                    redirect_url = reverse(
                        "parent_page" if user.is_parent else "patient_page",
                        args=[registry_code])
            else:
                redirect_url = reverse(_PATIENTS_LISTING)
        else:
            redirect_url = "%s?next=%s" % (reverse("two_factor:login"), reverse("login_router"))

        self._maybe_warn_about_password_expiry(request)

        return redirect(redirect_url)

    def _maybe_warn_about_password_expiry(self, request):
        user = request.user
        if not (user.is_authenticated and should_warn_about_password_expiry(user)):
            return

        days_left = days_to_password_expiry(user) or 0

        self._display_message(request, days_left)
        self._send_email_notification(user, days_left)

    def _display_message(self, request, days_left):
        sentence1 = ungettext(
            'Your password will expire in %(days)d days.',
            'Your password will expire in %(days)d days.', days_left) % {'days': days_left}
        link = ('<a href="%(url)s" class="alert-link">' + _('Change Password') +
                '</a>') % {'url': reverse('password_change')}
        sentence2 = _('Please use %(link)s to change it.') % {'link': link}
        msg = sentence1 + ' ' + sentence2

        messages.warning(request, mark_safe(msg))

    def _send_email_notification(self, user, days_left):
        template_data = {
            'user': user,
            'days_left': days_left,
        }

        for registry_model in user.registry.all():
            process_notification(
                registry_model.code,
                EventType.PASSWORD_EXPIRY_WARNING,
                template_data)
