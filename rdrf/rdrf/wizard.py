from django.core.urlresolvers import reverse


class NavigationError(Exception):
    pass


class NavigationWizard(object):
    """
    Allow user to navigate forward and back through demographics and clinical forms
    Conventionally, demographics is first, then clinical forms in position order
    Forms are skipped if not viewale by the user and we don't link to a questionnaire
    form
    """
    def __init__(self, user, registry_model, patient_model, current_form_model=None):
        """
        :param user:
        :param registry_model:
        :param patient_model:
        :param current_form_model: None is passed if on the demographic form as this has no model
        and is a special case, other the RegistryForm model instance
        :return:
        """
        self.user = user
        self.registry_model = registry_model
        self.patient_model = patient_model
        self.current_form_model = current_form_model
        self.links = self._construct_links()
        self.current_index = self._get_current_index()

    @property
    def next_link(self):
        index = self.move(1)
        return self.current_link(index)


    @property
    def previous_link(self):
        index = self.move(-1)
        return self.current_link(index)

    def move(self, steps):
        return (self.current_index + steps) % len(self.links)

    def _get_current_index(self):
        if self.current_form_model is None:
            # Demographics
            return 0  # demographics always first item
        else:
            index = 0
            for form_type, id, link in self.links:
                if form_type == "clinical" and id == self.current_form_model.pk:
                    return index
                else:
                    index += 1
            raise NavigationError("Form %s not in list" % self.current_form_model)

    def _construct_links(self):
        def form_link(form_model):
            link = reverse('registry_form', args=(self.registry_model.code,
                                                  form_model.id, self.patient_model.pk))
            return "clinical", form_model.pk, link

        demographic_link = ("demographic", None, reverse("patient_edit",
                                                         args=[self.registry_model.code, self.patient_model.pk]))

        consents_link = ("consents", None, reverse("custom_consent_form_view",
                                                   args=[self.registry_model.code, self.patient_model.pk]))

        clinical_form_links = [form_link(form) for form in self.registry_model.forms
                               if self.user.can_view(form) and not form.is_questionnaire]

        form_links = [demographic_link] + [consents_link] + clinical_form_links
        return form_links

    def current_link(self, index):
        _, _, link = self.links[index]
        return link
