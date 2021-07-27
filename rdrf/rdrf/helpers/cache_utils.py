import logging
from django.conf import settings
from django.core.cache import caches
from ccg_django_utils.conf import EnvConfig

logger = logging.getLogger(__name__)
env = EnvConfig()


def get_attrib(obj):
    if hasattr(obj, 'code'):
        return obj.code
    if hasattr(obj, 'name'):
        return obj.name


def use_query_cache(method):
    def wrapper(*args, **kwargs):

        if settings.CACHE_DISABLED or env.get("CACHE_DISABLED", False):
            return method(*args, **kwargs)

        obj = args[0]
        key = f"{get_attrib(obj)}_{method.__qualname__}_id{str(obj.pk)}"
        query_cache = caches["queries"]
        if key in query_cache:
            return query_cache.get(key)
        else:
            result = method(*args, **kwargs)
            query_cache.set(key, result)
            return result
    return wrapper
