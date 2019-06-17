from django.db import models
from registry.patients.models import Patient
from rdrf.models.definition.review_models import PatientReviewItem
from rdrf.models.definition.review_models import VerificationStatus
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RDRFContext

VER_CHOICES = ((VerificationStatus.VERIFIED, "Verified"),
               (VerificationStatus.NOT_VERIFIED, "Not Verified"),
               (VerificationStatus.UNKNOWN, "Unknown"))


class Verification(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    context = models.ForeignKey(RDRFContext, on_delete=models.CASCADE)
    patient_review_item = models.ForeignKey(PatientReviewItem,
                                            on_delete=models.CASCADE)
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    form_name = models.CharField(max_length=80,
                                 blank=True,
                                 null=True)
    section_code = models.CharField(max_length=80,
                                    blank=True,
                                    null=True)
    cde_code = models.CharField(max_length=30,
                                blank=True,
                                null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=1,
                              blank=True,
                              null=True,
                              choices=VER_CHOICES)
    username = models.CharField(max_length=80,
                                blank=True,
                                null=True)
    data = models.TextField(blank=True,
                            null=True)
    summary = models.TextField(blank=True,
                               null=True)

    def create_summary(self):
        """
        provide json blob of data so that if models are deleted we have context
        """
        self.summary = "to do"


def check_verification(registry_code,
                       patient_id,
                       context_id,
                       form_name,
                       section_code,
                       item_index,
                       cde_code,
                       value):
    from rdrf.models.definition.models import Registry
    from registry.patients.models import Patient
    from rdrf.models.definition.models import RDRFContext
    from rdrf.models.definition.verification_models import Verification

    registry_model = Registry.objects.get(code=registry_code)
    patient_model = Patient.objects.get(id=patient_id)
    context_model = RDRFContext.objects.get(id=context_id)
    STATUS_VERIFIED = "V"

    verifications = Verification.objects.filter(patient=patient_model,
                                                context=context_model,
                                                registry=registry_model,
                                                form_name=form_name,
                                                section_code=section_code,
                                                item=item_index,
                                                cde_code=cde_code,
                                                status=STATUS_VERIFIED).order_by("-created_date")
    verified = False
    if len(verifications) > 0:
        # this is the latest verfied value
        last_verification = verifications[0]
        if last_verification.data == str(value):
            verified = True

    return verified
