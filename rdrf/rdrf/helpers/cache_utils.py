import logging
from django.apps import apps
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

        key = f"{args[0]}_{args[1]}"
        query_cache = caches["queries"]
        if key in query_cache:
            return query_cache.get(key)
        else:
            result = function(*args, **kwargs)
            query_cache.set(key, result)
            return result
    return wrapper


@use_query_cache_for_model
def get_rdrf_model_id(class_name, value):
    model_class = apps.get_model("rdrf", class_name)
    try:
        return model_class.objects.filter(id=value).values_list('id', flat=True)[0]
    except Exception:
        return model_class.objects.filter(code=value).values_list('id', flat=True)[0]
