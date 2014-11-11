from django.forms import widgets
import logging

logger = logging.getLogger("registry_log")


class PatientRelativeLinkWidget(widgets.Widget):
    def render(self, name, value, attrs=None):
        script = """<script>
                        $(document).ready(function() { $("#" + "%s").siblings(".add-another").hide();});
                    </script>
                """ % attrs['id']
        if value is None:
            html = """<input type="checkbox" id="%s" name="%s">""" % (attrs['id'], name)
        else:
            #todo fix link
            html = """<a href='/admin/patients/patient/%s/'>Patient in registry</a>""" % value
        return html + script