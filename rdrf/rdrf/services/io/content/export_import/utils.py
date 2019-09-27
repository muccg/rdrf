import hashlib
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


class DelegateMixin():
    """Delegate to another object to get attributes.

    Tries to get attributes from object normally, but if attribute doesn't exist
    try getting attributes from the object set by delegate_to in __init__.
    """

    def __init__(self, delegate_to=None):
        self._delegate_to = delegate_to

    def __getattr__(self, attr):
        if not hasattr(self, '_delegate_to') or self._delegate_to is None:
            raise ValueError(
                "DelegateMixin not properly initialised with '_delegate_to' attribute")
        if hasattr(self._delegate_to, attr):
            return getattr(self._delegate_to, attr)
        raise AttributeError("'%s' object has no attribute '%s'" %
                             (self.__class__.__name__, attr))


class IndentedLogger(object):
    """Logger that indent the messages by indent_level number of spaces."""

    def __init__(self, logger, indent_level=4):
        self.logger = logger
        self.indentation = ' ' * indent_level

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(self.indentation + msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(self.indentation + msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(self.indentation + msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):
        self.logger.warning(self.indentation + msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(self.indentation + msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(self.indentation + msg, *args, **kwargs)

    fatal = critical

    def log(self, level, msg, *args, **kwargs):
        self.logger.critical(level, self.indentation + msg, *args, **kwargs)


def maybe_indent(logger):
    return IndentedLogger(logger) if hasattr(logger, 'indentation') else logger


def calculate_checksum_str(iterable):
    return calculate_checksum(s.encode("utf-8") for s in iterable)


def calculate_checksum(iterable):
    h = hashlib.md5()
    for item in iterable:
        h.update(item)
    return h.hexdigest()


def file_checksum(filename):
    with open(filename, "rb") as f:
        return calculate_checksum(f)


def app_schema_version(app_label):
    recorder = MigrationRecorder(connection)
    applied_migrations = sorted(
        (x[1] for x in recorder.applied_migrations() if x[0] == app_label))
    return calculate_checksum_str(applied_migrations)
