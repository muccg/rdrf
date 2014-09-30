from django.core import serializers
import copy
import json
from pymongo import MongoClient
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.core.files.storage import FileSystemStorage
from django.db.models.signals import post_save
from django.dispatch import receiver
import json

import registry.groups.models
from registry.utils import get_working_groups, get_registries

from rdrf.models import Registry

import logging
logger = logging.getLogger('patient')

from registry.utils import stripspaces
from django.conf import settings # for APP_NAME

file_system = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)

_MONGO_PATIENT_DATABASE = 'patients'
_MONGO_PATIENT_COLLECTION = 'patient'


class State(models.Model):
    short_name = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=30)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Doctor(models.Model):
    # TODO: Is it possible for one doctor to work with multiple working groups?
    family_name = models.CharField(max_length=100, db_index=True)
    given_names = models.CharField(max_length=100, db_index=True)
    surgery_name = models.CharField(max_length=100, blank=True)
    speciality = models.CharField(max_length=100)
    address = models.TextField()
    suburb = models.CharField(max_length=50, verbose_name="Suburb/Town")
    state = models.ForeignKey(State, verbose_name="State/Province/Territory")
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    class Meta:
        ordering = ['family_name']

    def __unicode__(self):
        return "%s %s" % (self.family_name.upper(), self.given_names)

class NextOfKinRelationship(models.Model):
    relationship = models.CharField(max_length=100, verbose_name="Relationship")

    class Meta:
        verbose_name = 'Next of Kin Relationship'

    def __unicode__(self):
        return self.relationship


class PatientManager(models.Manager):
    def get_by_registry(self, registry):
        return self.model.objects.filter(rdrf_registry__in=registry)

    def get_by_working_group(self, user):
        return self.model.objects.filter(working_group__in=get_working_groups(user))

    def get_filtered(self, user):
        return self.model.objects.filter(rdrf_registry__id__in=get_registries(user)).filter(working_group__in=get_working_groups(user)).distinct()
    
    def get_filtered_unallocated(self, user):
        return self.model.objects.filter(working_group__in=get_working_groups(user)).exclude(rdrf_registry__isnull=False)


class Patient(models.Model):
    if settings.INSTALL_NAME == 'dm1':   # Trac #16 item 9
        SEX_CHOICES = ( ("M", "Male"), ("F", "Female") )
    else:
        SEX_CHOICES = ( ("M", "Male"), ("F", "Female"), ("X", "Other/Intersex") )

    objects = PatientManager()
    rdrf_registry = models.ManyToManyField(Registry)
    working_group = models.ForeignKey(registry.groups.models.WorkingGroup, null=False, blank=False, verbose_name="Centre")
    consent = models.BooleanField(null=False, blank=False, help_text="The patient consents to be part of the registry and have data retained and shared in accordance with the information provided to them.", verbose_name="consent given")
    consent_clinical_trials = models.BooleanField(null=False, blank=False, help_text="The patient consents to be contacted about clinical trials or other studies related to their condition.", verbose_name="consent to allow clinical trials given", default=False)
    consent_sent_information = models.BooleanField(null=False, blank=False, help_text="The patient consents to be sent information on their condition.", verbose_name="consent to be sent information given", default=False)
    family_name = models.CharField(max_length=100, db_index=True)
    given_names = models.CharField(max_length=100, db_index=True)
    umrn = models.CharField(max_length=50, null=True, blank=True, db_index=True, verbose_name="Hospital/Clinic ID")
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(max_length=100, null=True, blank=True, verbose_name="Place of Birth")
    date_of_migration = models.DateField(help_text="If migrated", blank=True, null=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    home_phone = models.CharField(max_length=30, blank=True, null=True)
    mobile_phone = models.CharField(max_length=30, blank=True, null=True)
    work_phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    next_of_kin_family_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="family name")
    next_of_kin_given_names = models.CharField(max_length=100, blank=True, null=True, verbose_name="given names")
    next_of_kin_relationship = models.ForeignKey(NextOfKinRelationship, verbose_name="Relationship", blank=True, null=True)
    next_of_kin_address = models.TextField(blank=True, null=True, verbose_name="Address")
    next_of_kin_suburb = models.CharField(max_length=50, blank=True, null=True, verbose_name="Suburb/Town")
    next_of_kin_state = models.ForeignKey(State, verbose_name="State/Province/Territory", related_name="next_of_kin_set", blank=True, null=True)
    next_of_kin_postcode = models.IntegerField(verbose_name="Postcode", blank=True, null=True)
    next_of_kin_home_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="home phone")
    next_of_kin_mobile_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="mobile phone")
    next_of_kin_work_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="work phone")
    next_of_kin_email = models.EmailField(blank=True, null=True, verbose_name="email")
    next_of_kin_parent_place_of_birth = models.CharField(max_length=100, verbose_name="Place of birth of parents", blank=True, null=True)
    doctors = models.ManyToManyField(Doctor, through="PatientDoctor")
    active = models.BooleanField(default=True, help_text="Ticked if active in the registry, ie not a deleted record, or deceased patient.")
    inactive_reason = models.TextField(blank=True, null=True, verbose_name="Reason", help_text="Please provide reason for deactivating the patient")
    registry_specific_data = models.TextField(blank=True) # JSON!

    class Meta:
        ordering = ["family_name", "given_names", "date_of_birth"]

    def __unicode__(self):
        if self.active:
            return "%s %s" % (self.family_name, self.given_names)
        else:
            return "%s %s (Archived)" % (self.family_name, self.given_names)

    def save(self, *args, **kwargs):
        if hasattr(self, 'family_name'):
            self.family_name = stripspaces(self.family_name).upper()

        if hasattr(self, 'given_names'):
            self.given_names = stripspaces(self.given_names)

        if not self.pk:
            self.active = True
            
        super(Patient, self).save(*args, **kwargs)
        #regs = self._save_patient_mongo()

    def delete(self, *args, **kwargs):
        """
        If a user deletes a patient it's active flag will be true, so we should set it to false.
        If a superuser deletes a patient it's active flag is false, so we should delete the object.
        """
        if self.active:
            logger.debug("Archiving patient record.")
            self.active = False
            self.save()
        else:
            logger.debug("Deleting patient record.")
            super(Patient, self).delete(*args, **kwargs)
            
    def get_reg_list(self):
        return ', '.join([r.name for r in self.rdrf_registry.all()])
    get_reg_list.short_description = 'Registry'
    
    def as_json(self):
        return dict(
            obj_id=self.id,
            given_names=self.given_names,
            family_name=self.family_name,
            working_group=self.working_group.name,
            date_of_birth=str(self.date_of_birth)
            )

    @property
    def custom_data(self):
        if self.registry_specific_data:
            return json.loads(self.registry_specific_data)
        else:
            return {}

    @custom_data.setter
    def custom_data(self, new_data):
        json_data = json.dumps(new_data)
        self.registry_specific_data = json_data

    def set_registry_data(self, reg_code, data):
        custom_data = self.custom_data
        custom_data[reg_code] = data
        self.custom_data = custom_data

    def get_registry_data(self, reg_code):
        if reg_code in self.custom_data:
            return self.custom_data[reg_code]
        else:
            return {}


class AddressType(models.Model):
    type = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    
    def __unicode__(self):
        return "%s" % (self.type)


class PatientAddress(models.Model):
    patient = models.ForeignKey(Patient)
    address_type = models.ForeignKey(AddressType, default=1)
    address = models.TextField()
    suburb = models.CharField(max_length=50, verbose_name="Suburb/Town")
    state = models.CharField(max_length=20, verbose_name="State/Province/Territory")
    postcode = models.IntegerField()
    country = models.CharField(max_length=20)
    
    class Meta:
        verbose_name_plural = "Patient Addresses"
    

class PatientConsent(models.Model):
    patient = models.ForeignKey(Patient)
    form = models.FileField(upload_to='consents', storage=file_system, verbose_name="Consent form", blank=True, null=True)


class PatientDoctor(models.Model):
    patient = models.ForeignKey(Patient)
    doctor = models.ForeignKey(Doctor)
    relationship = models.CharField(max_length=50)

    class Meta:
        verbose_name = "medical professionals for patient"
        verbose_name_plural = "medical professionals for patient"



@receiver(post_save, sender=Patient)
def save_patient_mongo(sender, instance, **kwargs):
    patient_obj = Patient.objects.prefetch_related('rdrf_registry').get(pk=instance.pk)
    _save_patient_mongo(patient_obj)


def _save_patient_mongo(patient_obj):
    client = MongoClient()
    patient_db = client[_MONGO_PATIENT_DATABASE]
    patient_coll = patient_db[_MONGO_PATIENT_COLLECTION]
    
    json_str  = serializers.serialize("json", [patient_obj,])
    json_obj = json.loads(json_str)
    
    mongo_doc = patient_coll.find_one({'django_id': json_obj[0]['pk']})

    if mongo_doc:
        _update_mongo_obj(mongo_doc, json_obj[0]['fields'])
        patient_coll.save(mongo_doc)
    else:
        json_obj[0]['fields']['django_id'] = json_obj[0]['pk']
        json_obj[0]['fields']['rdrf_registry'] = _get_registry_for_mongo(patient_obj.rdrf_registry.all())
        patient_coll.save(json_obj[0]['fields'])


def _update_mongo_obj(mongo_doc, patient_model):
    for key, value in mongo_doc.iteritems():
        if key in ['rdrf_registry', ]:
            mongo_doc[key] = _get_registry_for_mongo(patient_model[key])
        if key not in ['django_id', '_id', 'rdrf_registry']:
            mongo_doc[key] = patient_model[key]


def _get_registry_for_mongo(regs):
    registry_obj = Registry.objects.filter(pk__in=regs)
    json_str = serializers.serialize("json", registry_obj)
    json_obj = json.loads(json_str)
    
    json_final = []
    
    for reg in json_obj:
        reg['fields']['id'] = reg['pk']
        del reg['fields']['splash_screen']
        json_final.append(reg['fields'])

    return json_final
