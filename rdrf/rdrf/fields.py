# Custom Fields
from django.forms import CharField, ChoiceField, URLField


class DatatypeFieldAlphanumericxxsx(URLField):
    pass


class ChoiceWithOtherPleaseSpecify(ChoiceField):
    pass


class CustomFieldC18587(CharField):
    def to_python(self, value):
        return value + "haha"
