import datetime
import logging
import threading

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.forms import ValidationError
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from useraudit import models as uam
from useraudit.middleware import get_request

logger = logging.getLogger(__name__)


_login_failure_limit = getattr(settings, 'LOGIN_FAILURE_LIMIT', 0)


_msg_default = 'Please enter a correct %(username)s and password (case-sensitive).'
_msg_limit = ('For security reasons, accounts are temporarily locked after '
              '%(login_failure_limit)d incorrect attempts.' % {'login_failure_limit' : _login_failure_limit})

# Making sure both text are available for translators indepenedent on the current LOGIN_FAILURE_LIMIT setting
_MSG_NO_LIMIT = _(_msg_default)
_MSG_WITH_LIMIT = _(_msg_default + ' ' + _msg_limit)
_MSG_LOCKED_OUT = _('For security reasons, your account has been locked.')
# TODO contact your registry owner or use unlock account


class RDRFAuthenticationForm(AuthenticationForm):
    error_messages = AuthenticationForm.error_messages

    _invalid_login_msg = _MSG_WITH_LIMIT if _login_failure_limit > 0 else _MSG_NO_LIMIT

    error_messages.update({
        'invalid_login': _(_invalid_login_msg)
    })

    def clean(self):
        try:
            super().clean()
        except ValidationError as e:
            improved_error = self._maybe_improve_error_msg(e)
            if improved_error is None:
                raise
            else:
                raise improved_error

    def _maybe_improve_error_msg(self, e):
        if getattr(e, 'code') != 'invalid_login':
            return None
        if _login_failure_limit == 0:
            return None
        login_failure_time_limit = getattr(settings, 'LOGIN_FAILURE_TOLERANCE_TIME', 0)
        if login_failure_time_limit == 0:
            return None

        username = self.cleaned_data.get('username')
        ip = extract_ip_address(self.request)
        since = timezone.now() - datetime.timedelta(minutes=login_failure_time_limit)

        def successfull_logins_since(login):
            return uam.LoginLog.objects.filter(username=username, ip_address=ip, timestamp__gt=login.timestamp)

        failed_logins = list(uam.FailedLoginLog.objects.filter(username=username, ip_address=ip, timestamp__gte=since))
        failed_logins_count = len(failed_logins)
        oldest_failed_login = failed_logins[_login_failure_limit - 1] if len(failed_logins) >= _login_failure_limit else None

        if failed_logins_count >= _login_failure_limit and not successfull_logins_since(oldest_failed_login).exists():
            return ValidationError(
                _MSG_LOCKED_OUT,
                code=e.code,
                params=e.params
            )
        return None


# Same as django.contrib.auth.forms.PasswordResetForm but also allows password reset functionality
# for inactive users if the Unlock Account feature is enabled and the user isn't explicitly prevented
# to unlock their account
class RDRFPasswordResetForm(PasswordResetForm):

    def get_users(self, email):
        if getattr(settings, 'ACCOUNT_SELF_UNLOCK_ENABLED', False):
            users = get_user_model()._default_manager.filter(
                prevent_self_unlock=False,
                email__iexact=email)
        else:
            users = get_user_model()._default_manager.filter(
                email__iexact=email, is_active=True)

        return (u for u in users if u.has_usable_password())


# Similar to django.contrib.auth.forms.PasswordResetForm but sends account unlock email link to the user.
# Also, sends a different email if the user tried to unlock their account but the account isn't locked.
class RDRFAccountUnlockForm(PasswordResetForm):

    def get_users(self, email):
        users = get_user_model()._default_manager.filter(email__iexact=email)
        return (u for u in users if u.is_active or not u.prevent_self_unlock)

    def save(self, domain_override=None,
             subject_template_name='registration/account_unlock_subject.txt',
             email_template_name='registration/account_unlock_email.html',
             account_unlocked_email_template_name='registration/account_unlock_requested_but_account_not_locked_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generates a one-use only link for resetting password and sends to the
        user.
        """
        email = self.cleaned_data["email"]
        for user in self.get_users(email):
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'user': user,
            }
            if not user.is_active:
                context['uid'] = urlsafe_base64_encode(force_bytes(user.pk))
                context['token'] = token_generator.make_token(user)
                context['protocol'] = 'https' if use_https else 'http'

            if extra_email_context is not None:
                context.update(extra_email_context)

            template_name = account_unlocked_email_template_name if user.is_active else email_template_name

            self.send_mail(subject_template_name, template_name, context, from_email, user.email)


# Same as django.contrib.auth.forms.SetPasswordForm but also reactivates the user if it is inactive
# end ACCOUNT_SELF_UNLOCK_ENABLED is True
class RDRFSetPasswordForm(SetPasswordForm):

    def save(self, commit=True):
        super().save(commit=False)
        if not self.user.is_active:
            if getattr(settings, 'ACCOUNT_SELF_UNLOCK_ENABLED', False):
                if not self.user.prevent_self_unlock:
                    self.user.is_active = True
            else:
                logger.warning('User "%s" resetted their password but their account is inactive '
                               'and settings.ACCOUNT_SELF_UNLOCK_ENABLED is NOT set.', self.user)
            if not self.user.is_active:
                request = get_request()
                if request:
                    messages.add_message(request, messages.ERROR, _('Your password has been changed, but your account is locked. '
                        'Please contact your registry owner for further information.'))
        if commit:
            self.user.save()
        return self.user


def extract_ip_address(request):
    ll = uam.LoginLogger()
    ip, _ = ll.extract_ip_address(request)
    return ip
