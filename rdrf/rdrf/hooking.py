import pkgutil
import inspect
import os
import logging

logger = logging.getLogger("registry_log")


def hook(hook_name):
    def decorator(func):
        func.rdrf_hook = hook_name
        return func
    return decorator


def run_hooks(hook_name, *args, **kwargs):
    import rdrf.hooks as defined_hooks_package
    defined_hooks_package_path = os.path.dirname(defined_hooks_package.__file__)
    hooks_to_run = []
    for _, defined_hook_module_name, _ in pkgutil.iter_modules(path=[defined_hooks_package_path]):
        defined_hook_module = __import__("rdrf.hooks." + defined_hook_module_name, fromlist=['rdrf.hooks'])
        for thing_name, thing in inspect.getmembers(defined_hook_module):
            if callable(thing) and hasattr(thing, "rdrf_hook") and thing.rdrf_hook == hook_name:
                logger.debug("found hook %s for %s" % (thing_name, hook_name))
                hooks_to_run.append(thing)

    for hook_func in hooks_to_run:
        logger.info("running hook func %s for %s" % (hook_func.__name__, hook_name))
        hook_func(*args, **kwargs)