from rest_framework import authentication
from rest_framework import exceptions
from registry.groups.models import CustomUser


import logging
logger = logging.getLogger(__name__)


class PromsAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        logger.info("authenticating proms")
        from django.conf import settings
        secret_token = request.META.get('HTTP_PROMS_SECRET_TOKEN')
        logger.info("token from request: %s" % secret_token)
        proms_secret_token = settings.PROMS_SECRET_TOKEN
        logger.info("settings proms token: %s" % proms_secret_token)
        proms_username = settings.PROMS_USERNAME
        logger.info("settings proms user: %s" % proms_username)

        if secret_token != proms_secret_token:
            logger.info("tokens don't match - failed to auth")
            raise Exception(request)
            return None

        try:
            user = CustomUser.objects.get(username=proms_username)
        except CustomUser.DoesNotExist:
            logger.info("proms user doesn't exist")
            raise exceptions.AuthenticationFailed('No such user')

        logger.info("authenticated as %s" % proms_username)

        return (user, None)
