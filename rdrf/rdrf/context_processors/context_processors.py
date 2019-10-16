from django.conf import settings
from rdrf.system_role import SystemRoles


def production(request):
    return {'production': settings.PRODUCTION}


def common_settings(request):
    return {
        'ACCOUNT_SELF_UNLOCK_ENABLED': settings.ACCOUNT_SELF_UNLOCK_ENABLED,
        'enable_pwd_change': settings.ENABLE_PWD_CHANGE
    }


def cic_system_role(request):
    return {
        'cic_system_role': settings.SYSTEM_ROLE in (SystemRoles.CIC_CLINICAL,
                                                    SystemRoles.CIC_DEV,
                                                    SystemRoles.CIC_PROMS
                                                    ),
    }
