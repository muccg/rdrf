import logging
import re
from django.core.cache import caches

logger = logging.getLogger(__name__)

illegal_characters = r"[:\"{}' <>,]"


def use_cache(function):
    def wrapper(*args, **kwargs):
        kwargs_str = re.sub(illegal_characters, '', str(kwargs))
        args_str = re.sub(illegal_characters, '', str(args))
        key = f"{function.__name__}_{kwargs_str}_{args_str}"
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
        obj = args[0]
        obj_str = re.sub(illegal_characters, '', str(obj))
        kwargs_str = re.sub(illegal_characters, '', str(kwargs))
        args_str = re.sub(illegal_characters, '', str(args))
        key = f"{method.__qualname__}_{obj_str}_id{str(obj.pk)}_{kwargs_str}_{args_str}"
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
