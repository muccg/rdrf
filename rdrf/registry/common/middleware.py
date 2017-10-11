from functools import reduce
import operator
import logging
import time

from django.db import connection
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger(__name__)


class TimeLogMiddleware(object):

    def process_request(self, request):
        request._start = time.time()

    def process_response(self, request, response):
        sqltime = reduce(operator.add, [float(q['time']) for q in connection.queries], 0.0)

        if hasattr(request, '_start'):
            d = {
                'method': request.method,
                'time': time.time() - request._start,
                'code': response.status_code,
                'url': smart_str(request.path_info),
                'sql': len(connection.queries),
                'sqltime': sqltime,
            }
            msg = '%(method)s "%(url)s" (%(code)s) %(time).2f (%(sql)dq, %(sqltime).4f)' % d
            logger.info(msg)
        return response


class EnforceTwoFactorAuthMiddleware(MiddlewareMixin):
    """
    This must be installed after
    :class:`~django.contrib.auth.middleware.AuthenticationMiddleware` and
    :class:`~django_otp.middleware.OTPMiddleware`.
    Users who are required to have two-factor authentication but aren't verified
    will always be redirected to the two-factor setup page.
    """
    def process_request(self, request):
        whitelisted_views = ('two_factor:login', 'two_factor:setup', 'two_factor:qr', 'logout', 'javascript-catalog')
        logger.debug([reverse(v) for v in whitelisted_views])
        if any([reverse(v) in request.path_info for v in whitelisted_views]):
            return None

        user = getattr(request, 'user', None)
        if user is None or user.is_anonymous:
            return None

        if not user.is_verified() and user.require_2_fact_auth:
            return HttpResponseRedirect(reverse('two_factor:setup'))

        return None
