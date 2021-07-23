import logging
import re
from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)


def use_cache(function):
    def wrapper(*args, **kwargs):

        if settings.CACHE_DISABLED:
            return function(*args, **kwargs)

        key = f"{function.__name__}"
        query_cache = caches["queries"]
        if key in query_cache:
            return query_cache.get(key)
        else:
            result = function(*args, **kwargs)
            query_cache.set(key, result)
            return result
    return wrapper


def use_object_cache(method):
    def wrapper(*args, **kwargs):

        if settings.CACHE_DISABLED:
            return method(*args, **kwargs)

        obj = args[0]
        key = f"{method.__qualname__}_id{str(obj.pk)}"
        query_cache = caches["queries"]
        if key in query_cache:
            logger.info(f"Fetching from Cache: {key}")
            return query_cache.get(key)
        else:
            result = method(*args, **kwargs)
            logger.info(f"Caching: {key}")
            query_cache.set(key, result)
            return result
    return wrapper


def get_cache(key=None):
    query_cache = caches["queries"]
    if key in query_cache:
        return query_cache.get(key)
    else:
        return None


def set_cache(key=None, value=None):
    query_cache = caches["queries"]
    query_cache.set(key, value)
