from django_redis import get_redis_connection
from django.conf import settings
from rdrf.system_role import SystemRoles


def get_or_add_registry_config():
    conn = get_redis_connection("blackboard")


def set_registry_config():
    if settings.SYSTEM_ROLE in [SystemRoles.CIC_CLINICAL, SystemRoles.CIC_DEV]:
        registry_code = "dummy"
        conn = get_redis_connection("blackboard")
        conn.hmset(f"{registry_code}-config", {"api-url": "https://hostname/api/v1/some_query/",
                                               "umrns": "",
                                               "api-token": "xyz"})
        
