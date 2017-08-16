import logging

from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from django.utils.translation import ugettext as _


logger = logging.getLogger(__name__)


_login_failure_limit = getattr(settings, 'LOGIN_FAILURE_LIMIT', 0)


_msg_default = 'Please enter a correct %(username)s and password (case-sensitive).'
_msg_limit = ('For security reasons, accounts are temporarily locked after '
              '%(login_failure_limit)d incorrect attempts.' % {'login_failure_limit' : _login_failure_limit})

# Making sure both text are available for translators indepenedent on the current LOGIN_FAILURE_LIMIT setting
_MSG_NO_LIMIT = _(_msg_default)
_MSG_WITH_LIMIT = _(_msg_default + ' ' + _msg_limit)


class RDRFAuthenticationForm(AuthenticationForm):
    error_messages = AuthenticationForm.error_messages

    _invalid_login_msg = _MSG_WITH_LIMIT if _login_failure_limit > 0 else _MSG_NO_LIMIT

    error_messages.update({
        'invalid_login': _(_invalid_login_msg)
    })
