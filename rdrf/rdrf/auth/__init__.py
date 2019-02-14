from django.conf import settings


def is_user_privileged(user):
    return not (user.is_patient or user.is_parent or user.is_carrier)


def can_user_self_unlock(user):
    return (
        getattr(settings, 'ACCOUNT_SELF_UNLOCK_ENABLED', False) and not
        is_user_privileged(user) and not user.prevent_self_unlock)
