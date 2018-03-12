from rdrf.models.verification.models import Annotation
from explorer.views import Humaniser


class VerificationError(Exception):
    pass


class VerifiableCDE:
    def __init__(self, registry_model, cde_dict):
        self.registry_model = registry_model
        self.cde_dict = cde_dict
        self.valid = False
        self.humaniser = Humaniser(self.registry_model)
        self._load(cde_dict)

    def _load(self, cde_dict):
        self.valid = False
        form_name = cde_dict.get("form", None)
        section_code = cde_dict.get("section", None)
        cde_code = cde_dict.get("cde", None)
        for form_model in self.registry_model.forms:
            if form_model.name == form_name:
                for section_model in form_model.section_models:
                    if section_model.code == section_code:
                        if not section_model.allow_multiple:
                            for cde_model in section_model.cde_models:
                                if cde_model.code == cde_code:
                                    self.form_model = form_model
                                    self.section_model = section_model
                                    self.cde_model = cde_model
                                    self.allow_multiple = False
                                    self.valid = True


    def get_data(self, patient_model, context_model=None):
        
        self._load(self.cde_dict)
        if not self.valid:
            raise VerificationError("Verification CDE dict: %s is not valid" % self.cde_dict)

        if context_model is None:
            context_model = patient_model.default_context(self.registry_model)


        try:

            cde_value = patient_model.get_form_value(self.registry_model.code,
                                                     self.form_model.name,
                                                     self.section_model.code,
                                                     self.cde_model.code,
                                                     context_id=context_model.pk)
        except KeyError:
            # form not filled in
            return "NOT ENTERED"

        return self.humaniser.display_value2(self.form_model,
                                                 self.section_model,
                                                 self.cde_model,
                                                 cde_value)

    @property
    def delimited_key(self):
        from rdrf.helpers.utils import mongo_key_from_models
        return mongo_key_from_models(self.form_model,
                                     self.section_model,
                                     self.cde_model)
    


    def is_current(self, user,registry_model, patient_model, context_model=None):
        """
        Is there no annotation or is the existing one out of date?
        """
        if context_model is None:
            context_model = patient_model.default_context(registry_model)
            
        annotations = [a for a in Annotation.objects.filter(patient_id=patient_model.pk,
                                                            context_id=context_model.pk,
                                                            form_name=self.form_model.name,
                                                            section_code=self.section_model.code,
                                                            cde_code=self.cde_model.code,
                                                            username=user.username).order_by("-timestamp")]

        if len(annotations) == 0:
            return False
        else:
            last_annotation = annotations[0]
            form_cde_value = self.get_data(patient_model, context_model)
            form_timestamp = patient_model.get_form_timestamp(self.form_model,
                                                              context_model=context_model)

            if form_timestamp is None:
                # this shouldn't happen - form not filled out
                # but then annotation shouldn't exist??
                return True

            # If patient edits the form timestamp will update even though particular cde might not have changed
                
            if last_annotation.timestamp < form_timestamp and self._value_changed(last_annotation.cde_value,
                                                                                  form_cde_value):
                return True

            return False

    def _value_changed(self, annotation_cde_value, form_cde_value):
            # complication here because the stored type is a string
            # let's just string compare
            return str(annotation_cde_value) != str(form_cde_value)


        
def get_verifiable_cdes(registry_model):
    if registry_model.has_feature("verification"):
        return filter(lambda v : v.valid == True,
                      [VerifiableCDE(registry_model, cde_dict)
                       for cde_dict in registry_model.metadata.get("verification_cdes", [])])
    
    return []


def user_allowed(user, registry_model, patient_model):
    """
    Can user see a cde value to verify - 
    """
    from rdrf.helpers.utils import consent_check
    return all([user.is_clinician(),
                user.in_registry(registry_model),
                patient_model.pk in [p.id for p in Patient.objects.filter(clinician=user)],
                consent_check(registry_model,
                              user,
                              patient_model,
                              "see_patient")])



def verifications_needed(user, registry_model, patient_model):
    verifiable_cdes = get_verifiable_cdes(registry_model)
    # ignore contexts for now
    return [ v for v in verifiable_cdes if not v.is_current(user,
                                                            registry_model,
                                                            patient_model)]


def verifications_apply(user):
    """
    Can we redirect to the verifications listing directly
    """
    if not user.is_clinician:
        return False
    if user.registry.count() != 1:
        return False
    registry_model = user.registry.first()
    return registry_model.has_feature("verification")

                                                            
                                                            
    
    
