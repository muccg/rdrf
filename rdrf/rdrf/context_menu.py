from django.core.urlresolvers import reverse


class PatientContextMenu(object):
    def __init__(self, user, registry_model, patient_model, context_model=None):
        """
        :param user: relative to user looking
        :param patient_model:
        :param registry_model:
        :param context_model:
        :return:
        """
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.context_model = context_model

    @property
    def html(self):
        patient_edit_link = self.get_patient_edit_link()
        #form_progress = self.get_form_progress()
        #action_buttons = self.get_actions()
        return patient_edit_link

    def get_patient_edit_link(self):
        registry_code = self.registry_model.code
        return "<a href='%s'>%s</a>" % \
               (reverse("patient_edit",
                        kwargs={"registry_code": registry_code,
                                "patient_id": self.patient_model.id}),
                self.patient_model.display_name)
