from django.template import loader, Context


class RDRFComponent(object):
    TEMPLATE = ""

    @property
    def html(self):
        return self._fill_template()

    def _fill_template(self):
        if not self.TEMPLATE:
            raise NotImplementedError("need to supply template")
        else:
            template = loader.get_template(self.TEMPLATE)
            data = self._get_template_data()
            context = Context(data)
            return template.render(context)

    def _get_template_data(self):
        # subclass should build dictionary for template
        return {}
                
        
class RDRFContextLauncherComponent(RDRFComponent):
    TEMPLATE = "rdrf_cdes/rdrfcontext_launcher.html"
    def __init__(self, registry_model, patient_model):
        self.registry_model = registry_model
        self.patient_model = patient_model


    def _get_template_data(self):
        existing_data_link = self._get_existing_data_link()

        return {
            "patient_listing_link" : existing_data_link,
            }

    def _get_existing_data_link(self):
        return self.patient_model.get_contexts_url(self.registry_model)

        
        

        
