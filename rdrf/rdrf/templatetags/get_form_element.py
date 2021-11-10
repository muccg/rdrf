from django import template
from rdrf.forms.dynamic.fields import ExternalField
import logging
register = template.Library()

logger = logging.getLogger(__name__)


class ElementWrapper:
    def __init__(self, dictionary, key, element):
        self.dictionary = dictionary  # this is actually a form instance ..
        self.key = key
        self.element = element

    def is_hidden(self):
        if self.is_external():
            if self._is_demographic_hidden_field():
                return True
            return False
        else:
            return self.element.is_hidden

    def is_external(self):
        return isinstance(self.element.field, ExternalField)

    def _is_demographic_hidden_field(self):
        from rdrf.models.definition.models import DemographicFields
        field_name = self.element.name
        try:
            _ = DemographicFields.objects.get(field=field_name)
            return True
        except:
            return False

    def __getattr__(self, attr):
        return getattr(self.element, attr)


@register.simple_tag
def get_form_element(dictionary, key):
    try:
        value = dictionary[key]
        return ElementWrapper(dictionary, key, value)
    except KeyError:
        # need this case after adding cdepolicy ...
        # the None value is skipped on the form
        return None
