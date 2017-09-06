from django.conf import settings


def common_settings(request):
    return {
        'ACCOUNT_SELF_UNLOCK_ENABLED': settings.ACCOUNT_SELF_UNLOCK_ENABLED,
    }
