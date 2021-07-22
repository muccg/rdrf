import logging
import re
from django.core.cache import caches

logger = logging.getLogger(__name__)

illegal_characters = r"[\"{}' ]"


def use_cache(function):
    def wrapper(*args, **kwargs):
        key = function.__name__ + re.sub(illegal_characters, '', str(kwargs))
        query_cache = caches["queries"]
        if key in query_cache:
            return query_cache.get(key)
        else:
            result = function(*args, **kwargs)
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
