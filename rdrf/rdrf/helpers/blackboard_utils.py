import os
from django_redis import get_redis_connection
from django.conf import settings
from rdrf.system_role import SystemRoles
import logging

logger = logging.getLogger(__name__)


def config_key(registry_code):
    return f"{registry_code}-config"


def has_registry_config(registry_code):
    conn = get_redis_connection("blackboard")
    return conn.exists(config_key(registry_code))


def get_api_hostname():
    return os.getenv("hostname")


def set_registry_config(registry_code):
    if settings.SYSTEM_ROLE in [SystemRoles.CIC_CLINICAL, SystemRoles.CIC_DEV]:
        logger.info(f"setting up registry blackboard config for {registry_code}")
        conn = get_redis_connection("blackboard")
        key = config_key(registry_code)
        api_token = settings.PROMS_SECRET_TOKEN
        hostname = get_api_hostname()
        api_url = f"https://{hostname}/intapi/v1/subscriptions/"

        if not has_registry_config(registry_code):
            conn.hmset(key, {"api-url": api_url,
                             "api-token": api_token})
