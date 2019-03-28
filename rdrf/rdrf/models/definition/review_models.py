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
    position = models.IntegerField(default=0)
    review = models.ForeignKey(Review, related_name="items", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=2,
                                 choices=ITEM_CHOICES)

    category = models.CharField(max_length=80, blank=True, null=True)
    name = models.CharField(max_length=80, blank=True, null=True)

    # the form or section models 
    form = models.ForeignKey(RegistryForm, blank=True, null=True, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, blank=True, null=True, on_delete=models.CASCADE)
    change_question_code = models.CharField(max_length=80, blank=True, null=True)  # cde code of change question
    current_status_question_code = models.CharField(max_length=80, blank=True, null=True)  # cde code of status question
    target_code = models.CharField(max_length=80, blank=True, null=True)  # the cde or section code or consent code


class ReviewStates:
    CREATED = "C"
    FINISHED = "F"


class VerificationStatus:
    VERIFIED = "V"
    NOT_VERIFIED = "N"
    UNKNOWN = "U"
    


class PatientReview(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, blank=True, null=True, on_delete=models.SET_NULL)  # the user who will fill out the review
    parent = models.ForeignKey(ParentGuardian, blank=True, null=True, on_delete=models.CASCADE)
    context = models.ForeignKey(RDRFContext, on_delete=models.CASCADE)
    token = models.CharField(max_length=80, unique=True, default=generate_token)
    created_date = models.DateTimeField(auto_now_add=True)
    completed_date = models.DateTimeField(blank=True)
    state = models.CharField(max_length=1, default=ReviewStates.CREATED)

    def generate_wizard(self):
        pass

    def save(self):
        for review_item in self.items:
            pass

    def email_link(self):
        pass


class PatientReviewItem(models.Model):
    created_date = models.DateTimeField(auto_now_add=True)
    patient_review = models.ForeignKey(PatientReview, related_name="items", on_delete=models.CASCADE)
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

    def save(self):
        pass

    
    
    
    
