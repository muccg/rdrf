from rest_framework import authentication
from rest_framework import exceptions
from registry.groups.models import CustomUser


import logging
logger = logging.getLogger(__name__)


def get_token(request, token):
    logger.info("proms auth getting token %s ..." % token)
    if token not in request.META:
        logger.info("%s not in request - returning None" % token)
        return None
    else:
        token_value = request.META.get(token)
        logger.info("%s = %s" % (token, token_value))
        return token_value


class PromsAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        logger.info("authenticating proms")
        from django.conf import settings
        secret_token = get_token(request, 'HTTP_PROMS_SECRET_TOKEN')
        if secret_token is None:
            secret_token = get_token(request, 'PROMS_SECRET_TOKEN')

        logger.info("token from request: %s" % secret_token)
        proms_secret_token = settings.PROMS_SECRET_TOKEN
        logger.info("settings proms token: %s" % proms_secret_token)
        proms_username = settings.PROMS_USERNAME
        logger.info("settings proms user: %s" % proms_username)

        if secret_token != proms_secret_token:
            logger.info("tokens don't match - failed to auth")
            return None

        try:
            user = CustomUser.objects.get(username=proms_username)
        except CustomUser.DoesNotExist:
            logger.info("proms user doesn't exist")
            raise exceptions.AuthenticationFailed('No such user')

        logger.info("authenticated as %s" % proms_username)

        return (user, None)
