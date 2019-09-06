import logging
from django.conf import settings
from registry.patients.models import Patient
from rest_framework.reverse import reverse

logger = logging.getLogger(__name__)


class CalculatedFieldScriptCreatorError(Exception):
    pass


class CalculatedFieldScriptCreator(object):

    def __init__(
            self,
            registry,
            registry_form,
            section,
            cde,
            injected_model=None,
            injected_model_id=None):

        self.registry_form = registry_form
        self.section = section
        self.cde = cde
        self.observer = self.cde.code
        self.script = None
        self.injected_model_id = injected_model_id

    def get_script(self):
        prefix = self.registry_form.name + settings.FORM_SECTION_DELIMITER + \
            self.section.code + settings.FORM_SECTION_DELIMITER
        observer_code = self.cde.code

        mod = __import__('rdrf.forms.fields.calculated_functions', fromlist=['object'])
        func = getattr(mod, f"{self.cde.code}_inputs")
        # required_cde_inputs = {}
        if func:
            cde_inputs = func()
        else:
            raise Exception(f"Trying to call an unknown calculated cde inputs function {self.cde.code}_inputs()")

        patient_model = Patient.objects.get(id=self.injected_model_id)
        patient_date_of_birth = patient_model.date_of_birth.__format__("%Y-%m-%d")
        wsurl = reverse("v1:calculatedcde-list")
        javascript = """
            <script>
            $(document).ready(function(){
                 const inputid = '#id_%s%s';

                 $(inputid).add_calculation({
                    cde_inputs: %s,
                    patient_sex: %s,
                    patient_date_of_birth: '%s',
                    observer: "%s",
                    wsurl: "%s",
                    });
                });

            </script>""" % (prefix, observer_code, cde_inputs, patient_model.sex, patient_date_of_birth, observer_code, wsurl)

        return javascript
