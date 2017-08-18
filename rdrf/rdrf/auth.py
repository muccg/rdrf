import datetime
import logging

from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.forms import ValidationError
from django.utils.translation import ugettext as _
from django.utils import timezone

from useraudit import models as uam

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
        login_failure_time_limit = getattr(settings, 'LOGIN_FAILURE_TOLERANCE_WINDOW', 0)
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


def extract_ip_address(request):
    ll = uam.LoginLogger()
    ip, _ = ll.extract_ip_address(request)
    return ip
