from django.urls import reverse


class Locator(object):
    GLYPHICON = "glyphicon-user"

    def __init__(self, registry_model, instance):
        self.registry_model = registry_model
        self.instance = instance

    @property
    def link(self):
        """
        return html with glyphicon
        e.g. <i class="text-muted"><span class="glyphicon glyphicon-user" aria-hidden="true"></span> XXXFred FLINTSTONE</i>
        """
        if self.instance is None:
            return ""
        descriptor = self.get_description()
        link = self.get_link()
        location_link = "<a href='%s'>%s</a>" % (link, descriptor)
        return """<i class="text-muted"><span class="glyphicon {0}" aria-hidden="true"></span> {1}</i>""".format(
            self.GLYPHICON, location_link)

    def get_description(self):
        raise NotImplementedError("subclass responsiblity")

    def get_link(self):
        raise NotImplementedError("subclass responsiblity")

    def __str__(self):
        return self.link


class PatientLocator(Locator):

    def get_description(self):
        return self.instance.display_name

    def get_link(self):
        patient_edit_url = reverse(
            'patient_edit',
            args=[
                self.registry_model.code,
                self.instance.id])
        return patient_edit_url
