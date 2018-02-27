from django.db import models
from django.utils.translation import ugettext as _

from .definition.models  import Registry, RegistryForm, Section, CommonDataElement
from registry.groups.models import CustomUser

class VerificationStatus:
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"
    UPDATED = "updated"
    
    
    

class Verification(models.Model):
    """
    Stores the result of a vefication from a clinician
    """
    
    VERIFICATION_STATES = (
        (VerificationStatus.VERIFIED, _(VerificationStatus.VERIFIED)),
        (VerficationStatus.UNVERIFIED, _(VerificationStatus.UNVERIFIED)),
        (VerificationStatus.DISPUTED, _(VerificationStatus.DISPUTED)),
        (VerificationStatus.UPDATED, _(VerificationStatus.UPDATED)))
    
    user = models.ForeignKey(CustomUser)
    patient_id = models.IntegerField(db_index=True)
    context_id = models.IntegerField(db_index=True, blank=True, null=True)
    status = models.CharField(max_length=50, choices=VERIFICATION_STATES)
    registry_code = models.CharField(max_length=10)
    form_name = models.CharField(max_length=80)
    section_code = models.CharField(max_length=100)
    item = models.IntegerField(null=True)
    cde_code = models.CharField(max_length=30)
    value = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    comment = models.TextField()








    
    
