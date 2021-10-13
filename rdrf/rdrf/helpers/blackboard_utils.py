import os
from django_redis import get_redis_connection
from django.conf import settings
from rdrf.system_role import SystemRoles
import logging

logger = logging.getLogger(__name__)


def broker_key(registry_code):
    return f"broker-url:{registry_code}"


def get_api_hostname():
    return os.getenv("hostname")


def set_broker_url(redis, registry_code):
    key = broker_key(registry_code)
    value = settings.CELERY_BROKER_URL
    redis.set(key, value)


def set_registry_config(registry_code):
    if settings.SYSTEM_ROLE in [SystemRoles.CIC_CLINICAL, SystemRoles.CIC_DEV]:
        logger.info(f"setting up registry blackboard config for {registry_code}")
        conn = get_redis_connection("blackboard")
        set_broker_url(conn, registry_code)


def setup_message_router_subscription(registry_code, umrn):
    logger.info(f"setting up hub subscription for registry code {registry_code} umrn {umrn}")
    conn = get_redis_connection("blackboard")
    conn.sadd(f"umrns:{registry_code}", umrn)
