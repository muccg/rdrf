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


def use_query_cache_for_model(function):
    def wrapper(*args, **kwargs):

        if settings.CACHE_DISABLED or env.get("CACHE_DISABLED", False):
            return function(*args, **kwargs)
        model_class = args[0].__name__
        field = args[1]
        value = args[2]
        key = f"{model_class}_{field}_{value}"
        query_cache = caches["queries"]
        if key in query_cache:
            return query_cache.get(key)
        else:
            result = function(*args, **kwargs)
            query_cache.set(key, result)
            return result
    return wrapper


@use_query_cache_for_model
def get_rdrf_model_id(model_class, field, value):
    filter_condition = f"{field}__iexact"
    return model_class.objects.filter(**{filter_condition: value}).values_list('id', flat=True)[0]
