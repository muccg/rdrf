from django.db import models
from django.utils.translation import ugettext as _

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import RDRFContext
from rdrf.helpers.utils import generate_token

from registry.groups.models import CustomUser
from registry.patients.models import Patient
from registry.patients.models import ParentGuardian

import logging

logger = logging.getLogger(__name__)


class InvalidItemType(Exception):
    pass


def generate_reviews(registry_model):
    reviews_dict = registry_model.metadata.get("reviews", {})
    for review_name, review_sections in reviews_dict.items():
        r = Review(registry=registry_model,
                   name=review_name)
        r.save()


class Review(models.Model):
    registry = models.ForeignKey(Registry, related_name="reviews", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)  # e.g. annual review , biannual review
    code = models.CharField(max_length=80)  # used for url

    def create_for_patient(self, patient, context_model=None):
        if context_model is None:
            context_model = patient.default_context(self.registry)
        pr = PatientReview(review=self,
                           patient=patient,
                           context=context_model)
        pr.save()
        return pr

    def create_for_parent(self, parent):
        for child in parent.children:
            pr = self.create_for_patient(child)
            pr.parent = parent
            pr.save()

    @property
    def view_name(self):
        return self.registry.code + "_review_" + self.code

    @property
    def view(self):
        from rdrf.views.wizard_views import ReviewWizardGenerator
        generator = ReviewWizardGenerator(self)
        wizard_class = generator.create_wizard_class()
        return wizard_class.as_view()

    @property
    def url_pattern(self):
        from django.urls import re_path
        path = "^reviews/%s/%s$" % (self.registry.code,
                                    self.code)
        return re_path(path, self.view, name=self.view_name)


class REVIEW_ITEM_TYPES:
    CONSENT_FIELD = "CF"        # continue to consent
    DEMOGRAPHICS_FIELD = "DF"   # update some data
    SECTION_CHANGE =  "SC"      # monitor change in a given section
    MULTISECTION_ITEM = "MI"    # add to a list of items  ( e.g. new therapies since last review)
    MULTISECTION_UPDATE = "MU"  # replace / update a set of items  ( necessary?)
    VERIFICATION = "V"


ITEM_CHOICES = ((REVIEW_ITEM_TYPES.CONSENT_FIELD, _("Consent Item")),
                (REVIEW_ITEM_TYPES.DEMOGRAPHICS_FIELD, _("Demographics Field")),
                (REVIEW_ITEM_TYPES.SECTION_CHANGE, _("Section Monitor")),
                (REVIEW_ITEM_TYPES.MULTISECTION_ITEM, _("Add to Section")),
                (REVIEW_ITEM_TYPES.MULTISECTION_UPDATE, _("Update Section")),
                (REVIEW_ITEM_TYPES.VERIFICATION, _("Verification Section")))


class ReviewItem(models.Model):
    """
    A unit of a review
    """
    code = models.CharField(max_length=80)
    position = models.IntegerField(default=0)
    review = models.ForeignKey(Review, related_name="items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=2,
                                 choices=ITEM_CHOICES)

    category = models.CharField(max_length=80, blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)
    fields = models.TextField(blank=True)  # used for demographics
    summary = models.TextField(blank=True)

    # the form or section models 
    form = models.ForeignKey(RegistryForm, blank=True, null=True, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, blank=True, null=True, on_delete=models.CASCADE)
    change_question_code = models.CharField(max_length=80, blank=True, null=True)  # cde code of change question
    current_status_question_code = models.CharField(max_length=80, blank=True, null=True)  # cde code of status question
    target_code = models.CharField(max_length=80, blank=True, null=True)  # the cde or section code or consent code

    def update_data(self, patient_model, parent_model, context_model, form_data):
        if self.item_type == REVIEW_ITEM_TYPES.CONSENT_FIELD:
            self._update_consent_data(patient_model, form_data)
        elif self.item_type == REVIEW_ITEM_TYPES.DEMOGRAPHICS_FIELD:
            self._update_demographics_data(patient_model, form_data)
        elif self.item_type == REVIEW_ITEM_TYPES.SECTION_CHANGE:
            self._update_section_data(patient_model, context_model, form_data)
        elif self.item_type == REVIEW_ITEM_TYPES.MULTISECTION_ITEM:
            self._add_multisection_data(patient_model, context_model, form_data)
        elif self.item_type == REVIEW_ITEM_TYPES.VERIFICATION:
            self._update_verification(patient_model, context_model, form_data)
        else:
            raise InvalidItemType(self.item_type)

    def _update_consent_data(self, patient_model, form_data):
        from rdrf.models.definition.models import ConsentQuestion
        for field_key in form_data:
            answer = form_data[field_key]
            logger.debug("consent %s = %s" % (field_key, answer))
            key_parts = field_key.split("_")
            question_pk = int(key_parts[3])
            consent_question_model = ConsentQuestion.objects.get(id=question_pk)
            patient_model.set_consent(consent_question_model, answer)


    def _update_section_data(self, patient_model, context_model, form_data):
        logger.debug("update section data : todo!")

    def _update_demographics_data(self, patient_model, form_data):
        logger.debug("update demographics data : todo!")

    def _add_multisection_data(self, patient_model, context_model, form_data):
        logger.debug("update multisection data : todo!")

    def _update_verification(self, patient_model, context_model, form_data):
        pass

    def get_data(self, patient_model, context_model):
        # get previous responses so they can be displayed
        if self.item_type == REVIEW_ITEM_TYPES.CONSENT_FIELD:
            return self._get_consent_data(patient_model)
        elif self.item_type == REVIEW_ITEM_TYPES.DEMOGRAPHICS_FIELD:
            return self._get_demographics_data(patient_model)
        elif self.item_type == REVIEW_ITEM_TYPES.SECTION_CHANGE:
            return self._get_section_data(patient_model, context_model)

        # otherwise
        return []

    def _get_consent_data(self, patient_model):
        from rdrf.models.definition.models import ConsentSection
        from rdrf.models.definition.models import ConsentQuestion
        from registry.patients.models import ConsentValue
        consent_section_code, consent_question_code = self.target_code.split("/")
        consent_section_model = ConsentSection.objects.get(code=consent_section_code,
                                                           registry=self.review.registry)

        consent_question_model = ConsentQuestion.objects.get(code=consent_question_code,
                                                             section=consent_section_model)

        field_label = consent_question_model.question_label

        try:
            consent_value = ConsentValue.objects.get(consent_question=consent_question_model,
                                                     patient_id=patient_model.pk)
            answer = consent_value.answer

        except ConsentValue.DoesNotExist:
            answer = False

        return [(field_label, answer)]

    def _get_demographics_data(self, patient_model):
        is_address = self.fields.lower().strip() in ["postal_address", "home_address", "address"]
        if is_address:
            return self._get_address_data(patient_model)
        else:
            return self._get_demographics_fields(patient_model)

    def _get_address_data(self, patient_model):
        from registry.patients.models import PatientAddress
        from registry.patients.models import AddressType 
        pairs = []
        field = self.fields.lower().strip()
        if field == "postal_address":
            address_type = AddressType.objects.get(type="Postal")
        else:
            address_type = AddressType.objects.get(type="Home")


        try:
            address = PatientAddress.objects.get(patient=patient_model,
                                             address_type=address_type)
        except PatientAddress.DoesNotExist:
            return []
            
        pairs.append(("Address Type", address_type.description))
        pairs.append(("Address", address.address))
        pairs.append(("Suburb", address.suburb))
        pairs.append(("Country",address.country))
        pairs.append(("State", address.state))
        pairs.append(("Postcode", address.postcode))
        return pairs

    def _get_demographics_fields(self, patient_model):
        return []

    def _get_section_data(self, patient_model, context_model):
        patient_data = patient_model.get_dynamic_data(self.review.registry,
                                                      collection="cdes",
                                                      context_id=context_model.pk)

        

        
        
                
                
        


class ReviewStates:
    CREATED = "C"         # created , patient hasn't filled out yet
    DATA_COLLECTED = "D"  # data collected from review and stored in patient review items
    FINISHED = "F"        # data fanned out without error from review items
    ERROR = "E"           # if an error stops the fan out


class VerificationStatus:
    VERIFIED = "V"
    NOT_VERIFIED = "N"
    UNKNOWN = "U"


class PatientReviewItemStates:
    CREATED = "C"               # model instance created , waiting for data
    DATA_COLLECTED = "D"        # data collected
    FINISHED = "F"


class PatientReview(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.SET_NULL)  # the user who will fill out the review
    parent = models.ForeignKey(ParentGuardian, blank=True, null=True, on_delete=models.CASCADE)
    context = models.ForeignKey(RDRFContext, on_delete=models.CASCADE)
    token = models.CharField(max_length=80, unique=True, default=generate_token)
    created_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    state = models.CharField(max_length=1, default=ReviewStates.CREATED)

    def email_link(self):
        pass

    def create_review_items(self):
        for item in self.review.items.all():
            pri = PatientReviewItem(patient_review=self,
                                    review_item=item)
            pri.save()


class PatientReviewItem(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    patient_review = models.ForeignKey(PatientReview, related_name="items", on_delete=models.CASCADE)
    state = models.CharField(max_length=1, default=PatientReviewItemStates.CREATED)
    review_item = models.ForeignKey(ReviewItem, on_delete=models.CASCADE)
    has_changed = models.CharField(max_length=1,
                                   blank=True,
                                   null=True)

    current_status = models.CharField(max_length=1,
                                      blank=True,
                                      null=True)
    verification_status = models.CharField(max_length=1,
                                           blank=True,
                                           null=True)
    data = models.TextField(blank=True, null=True)  # json data

    def update_data(self, cleaned_data):
        self.data = self._encode_data(cleaned_data)
        self.state = PatientReviewItemStates.DATA_COLLECTED
        self.save()
        # fan out the review data from a patient to the correct place
        # the model knows how to update the data
        self.review_item.update_data(self.patient_review.patient,
                                     self.patient_review.parent,
                                     self.patient_review.context,
                                     cleaned_data)
        self.state = PatientReviewItemStates.FINISHED
        self.save()

    def _encode_data(self, data):
        import json
        return json.dumps(data)
