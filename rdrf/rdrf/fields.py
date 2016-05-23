# Custom Fields
from django.forms import CharField, ChoiceField, URLField
from django.core.exceptions import ValidationError

class DatatypeFieldAlphanumericxxsx(URLField):
    pass


class ChoiceWithOtherPleaseSpecify(ChoiceField):
    pass


class CustomFieldC18587(CharField):

    def to_python(self, value):
        return value + "haha"


class ChoiceFieldNoValidation(ChoiceField):

    def validate(self, value):
        pass

class ChoiceFieldNonBlankValidation(ChoiceField):

    def validate(self, value):
        if not value:
            raise ValidationError("A value must be selected")
