from django.forms import widgets
import logging
import hashlib
import random
from django.core.urlresolvers import reverse

logger = logging.getLogger("registry_log")


class PatientRelativeLinkWidget(widgets.Widget):

    """
    This provides a link to the patient created from the relative
    Before the patient is created , it provides a checkbox ( Similar to the delete checkbox provided against other inlines )
    - checking it signals  that a patient should be created from the patient relative data supplied.
    There is also javascript to hide the green plus symbol to avoid the popup
    """
    REGISTRY_CODE = 'fh'   # how to set!

    def render(self, name, value, attrs=None):
        if value is None:
            return """<input type="checkbox" id="%s" name="%s">""" % (attrs['id'], name)
        elif value == 'on':
            return """<input type="checkbox" value="on" id="%s" name="%s">""" % (attrs['id'], name)
        else:
            reg_code = self.REGISTRY_CODE

            hidden_field = """<input type=hidden id="%s" name="%s" value="%s">""" % (
                attrs['id'], name, value)  # ensure that the link to patient not lost on submission!

            patient_url = reverse("patient_edit", args=[reg_code, value])

            html = """<a  href='%s'>Patient in registry</a>%s""" % (patient_url, hidden_field)
            return html
