import datetime
from django.contrib.postgres.fields import JSONField

__all__ = ["DataField"]


class DataField(JSONField):
    """
    JSONField doesn't allow saving dates or datetimes.

    This field is jsonb column with python dates/time objects
    converted to strings.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("default", dict)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        _convert_datetime_to_str(value)
        return super().get_prep_value(value)

    def to_python(self, value):
        _convert_datetime_to_str(value)
        return value


def _convert_datetime_to_str(data):
    if isinstance(data, list):
        for x in data:
            _convert_datetime_to_str(x)
    elif hasattr(data, "items"):
        for k, value in data.items():
            if isinstance(value, (datetime.date, datetime.datetime)):
                data[k] = value.isoformat()
            else:
                # recurse on multisection data
                _convert_datetime_to_str(value)
