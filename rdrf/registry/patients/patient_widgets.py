from django.forms import widgets
import logging
import hashlib
import random
logger = logging.getLogger("registry_log")


class PatientRelativeLinkWidget(widgets.Widget):
    def render(self, name, value, attrs=None):
        script = """<script>
                        $(document).ready(function() { $("#" + "%s").siblings(".add-another").hide();});
                    </script>
                """
        if value is None:
            control_id = attrs['id']
            html = """<input type="checkbox" id="%s" name="%s">""" % (attrs['id'], name)
        else:
            control_id = hashlib.sha1(str(random.random())).hexdigest()  # random guid for id ensures we can locate the link to hide the + easily
            hidden_field = """<input type=hidden id="%s" name="%s" value="%s">""" % (attrs['id'], name, value)  # ensure that the link to patient not lost on submission!
            html = """<a id="%s" href='/admin/patients/patient/%s/'>Patient in registry</a>%s""" % (control_id, value, hidden_field)
        return html + script % control_id