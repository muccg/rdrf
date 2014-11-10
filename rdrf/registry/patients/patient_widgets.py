from django.forms import widgets
import logging

logger = logging.getLogger("registry_log")


class PatientRelativeLinkWidget(widgets.Widget):
    def render(self, name, value, attrs=None):
        if value is None:
            widget_html = """<input type="checkbox" id="%s" name="%s">""" % (attrs['id'], name)
            return widget_html
        else:
            #todo fix link
            link = """<a href='/admin/patients/patient/%s/'>Patient in registry</a>""" % value
            return link

