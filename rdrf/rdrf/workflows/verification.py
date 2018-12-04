from explorer.views import Humaniser
from rdrf.models.verification.models import Annotation

import logging
logger = logging.getLogger(__name__)


class VerificationError(Exception):
    pass


class NoData:
    pass

class VerificationStatus:
    UNVERIFIED = "unverified"    # clinician has not checked or does not know
    VERIFIED = "verified"        # clinician agrees with patient supplied value
    CORRECTED = "corrected"      # clinican provides a new value


INSPECTED = [VerificationStatus.VERIFIED,
             VerificationStatus.CORRECTED]


class VerifiableCDE:
    def __init__(self,
                 registry_model,
                 cde_dict=None,
                 form_model=None,
                 section_model=None,
                 cde_model=None,
                 position=None):
        self.registry_model = registry_model
        self.cde_dict = cde_dict
        self.valid = False
        self.position = position

        self.humaniser = Humaniser(self.registry_model)
        if cde_dict is not None:
            self._load(cde_dict)

        # Allow easy setup in POST views
        if form_model is not None:
            self.form_model = form_model
        if section_model is not None:
            self.section_model = section_model
        if cde_model is not None:
            self.cde_model = cde_model

        self.patient_data = NoData
        self.clinician_data = NoData
        self.patient_display_value = NoData
        self.status = VerificationStatus.UNVERIFIED
        self.comments = ""


    @property
    def display_value(self):
        def disp(value):
            return self.humaniser.display_value2(self.form_model,
                                                 self.section_model,
                                                 self.cde_model,
                                                 value)

        if self.status == "corrected":
            return disp(self.clinician_data)
        elif self.status == "verified":
            return disp(self.patient_data)
            

    def set_clinician_value(self, raw_value):
        # field has already been validated so type casts are safe
        if self.cde_model.datatype == "integer":
            self.clinician_data = int(raw_value)
        elif self.cde_model.datatype in ["float", "decimal", "numeric"]:
            self.clinician_data = float(raw_value)
        else:
            # everything else is string
            self.clinician_data = raw_value

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

    def get_data(self, patient_model, context_model, display=True):
        # gets the data the Patient has entered ( if at all)

        if not all([self.registry_model,
                    self.section_model,
                    self.cde_model]):

            self._load(self.cde_dict)
        else:
            self.valid = True
        if not self.valid:
            raise VerificationError("Verification CDE dict: %s is not valid" % self.cde_dict)

        try:

            cde_value = patient_model.get_form_value(self.registry_model.code,
                                                     self.form_model.name,
                                                     self.section_model.code,
                                                     self.cde_model.code,
                                                     context_id=context_model.pk)

            self.patient_data = cde_value

        except KeyError:
            # form not filled in
            return "NOT ENTERED"

        self.patient_display_value = self.humaniser.display_value2(self.form_model,
                                                                   self.section_model,
                                                                   self.cde_model,
                                                                   cde_value)

        if display:
            return self.patient_display_value
        else:
            return self.patient_data

    @property
    def delimited_key(self):
        from rdrf.helpers.utils import mongo_key_from_models
        return mongo_key_from_models(self.form_model,
                                     self.section_model,
                                     self.cde_model)

    def has_annotation(self, user, registry_model, patient_model, context_model):
        """
        Is there no annotation or is the existing one out of date because the value of
        the cde has changed?
        """
        def carp(msg):
            logger.debug("Annotations Patient %s Context %s CDE %s: %s" % (patient_model,
                                                                           context_model.id,
                                                                           self.cde_model.code,
                                                                           msg))

        annotations_query = Annotation.objects.filter(patient_id=patient_model.pk,
                                                      context_id=context_model.pk,
                                                      form_name=self.form_model.name,
                                                      section_code=self.section_model.code,
                                                      cde_code=self.cde_model.code,
                                                      username=user.username).order_by("-timestamp")

        if annotations_query.count() == 0:
            carp("no annotations")
            return None
        else:
            last_annotation = annotations_query.first()
            carp("last annotation status = %s" % last_annotation.annotation_type)
            form_cde_value = self.get_data(patient_model, context_model, display=False)
            if not self._value_changed(last_annotation.cde_value, form_cde_value):
                carp("value changed : patient value = [%s] annotation value = [%s]" % (last_annotation.cde_value,
                                                                                       form_cde_value))

                logger.debug("returning last annotation as values have not changed: %s" % last_annotation)
                return last_annotation
            else:
                logger.debug("returning None as values have changed so new verification required")
                return None

        # cde will show up as unverified

        return None

    def _value_changed(self, annotation_cde_value, form_cde_value):
            # complication here because the stored type is a string
            # let's just string compare
        logger.debug("checking value changed for cde %s" % self.cde_model.code)
        logger.debug("ann cde value = %s" % annotation_cde_value)
        logger.debug("form cde value = %s" % form_cde_value)
        values_differ = str(annotation_cde_value) != str(form_cde_value)
        if values_differ:
            logger.debug("values differ")
            return True
        else:
            logger.debug("values are the same..")
            return False


def get_verifiable_cdes(registry_model):
    if registry_model.has_feature("verification"):
        return filter(lambda v: v.valid,
                      [VerifiableCDE(registry_model, cde_dict, position=index)
                       for index, cde_dict in enumerate(registry_model.metadata.get("verification_cdes", []))])

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

def get_verifications(user, registry_model, patient_model, context_model):
    verifiable_cdes = get_verifiable_cdes(registry_model)
    verifications = []
    for v in verifiable_cdes:
        logger.debug("getting verification for cde %s" % v.cde_model.code)

        last_annotation = v.has_annotation(user,
                                           registry_model,
                                           patient_model,
                                           context_model)

        if last_annotation is not None:
            logger.debug("found an annotation")
            v.status = last_annotation.annotation_type
            logger.debug("status = %s" % v.status)
            v.comments = last_annotation.comment
            logger.debug("comments = %s" % v.comments)
            v.clinician_data = last_annotation.cde_value

        else:
            logger.debug("no annotation")
            v.status = VerificationStatus.UNVERIFIED

        verifications.append(v)

    return verifications


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


def create_annotations(user, registry_model, patient_model, context_model, verified=[], corrected=[]):
    for v in corrected:
        correct_value = v.clinician_data
        annotation = Annotation()
        annotation.patient_id = patient_model.pk
        annotation.context_id = context_model.id
        annotation.annotation_type = "corrected"
        annotation.registry_code = registry_model.code
        annotation.form_name = v.form_model.name
        annotation.section_code = v.section_model.code
        annotation.cde_code = v.cde_model.code
        annotation.username = user.username
        annotation.comment = v.comments
        annotation.cde_value = str(correct_value)
        annotation.orig_value = str(v.patient_data)
        annotation.save()

        patient_model.set_form_value(v.registry_model.code,
                                     v.form_model.name,
                                     v.section_model.code,
                                     v.cde_model.code,
                                     correct_value,
                                     save_snapshot=True,
                                     user=user)

    for v in verified:
        annotation = Annotation()
        annotation.patient_id = patient_model.pk
        annotation.context_id = context_model.id
        annotation.annotation_type = "verified"
        annotation.registry_code = registry_model.code
        annotation.form_name = v.form_model.name
        annotation.section_code = v.section_model.code
        annotation.cde_code = v.cde_model.code
        annotation.username = user.username
        annotation.comment = v.comments
        annotation.cde_value = str(v.patient_data)
        annotation.orig_value = str(v.patient_data)
        annotation.save()

def send_participant_notification(registry_model, clinician_user, patient_model, diagnosis):
    from rdrf.services.io.notifications.email_notification import process_notification
    from rdrf.events.events import EventType
    from registry.patients.models import ParentGuardian
    if diagnosis is None:
        return
    participants = [pg for pg in ParentGuardian.objects.filter(patient=patient_model)]
    if len(participants) > 0:
        participant = participants[0]
    else:
        raise Exception("No participant associated with patient")

    patient_name = "%s %s" % (patient_model.given_names, patient_model.family_name)

    template_data = {"participant_email": participant.user.email,
                     "diagnosis": diagnosis,
                     "patient_name": patient_name,
                     "clinician_name": clinician_user.last_name,
                     }

    process_notification(registry_model.code,
                         EventType.PARTICIPANT_CLINICIAN_NOTIFICATION,
                         template_data)

def get_diagnosis(registry_model, verifications):
    diagnosis_code = registry_model.diagnosis_code
    logger.debug("diagnosis code = %s" % diagnosis_code)
    if not diagnosis_code:
        return None
    for v in verifications:
        if v.cde_model.code == diagnosis_code:
            if v.status in INSPECTED:
                return v.display_value

    return None
