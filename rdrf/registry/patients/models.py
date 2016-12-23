import json
import datetime
import os.path
from operator import attrgetter

from django.core.exceptions import ValidationError
from django.core import serializers
from django.core.files.storage import DefaultStorage
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save, m2m_changed, post_delete
from django.dispatch import receiver
import pycountry

from rdrf.dynamic_data import DynamicDataWrapper
from rdrf.models import Registry, Section, ConsentQuestion
from rdrf.hooking import run_hooks
import registry.groups.models
from registry.utils import get_working_groups, get_registries, stripspaces
from registry.groups.models import CustomUser


import logging
logger = logging.getLogger(__name__)

_6MONTHS_IN_DAYS = 183


class State(models.Model):
    short_name = models.CharField(max_length=3, primary_key=True)
    name = models.CharField(max_length=30)
    country_code = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Doctor(models.Model):
    SEX_CHOICES = (("1", "Male"), ("2", "Female"), ("3", "Indeterminate"))

    # TODO: Is it possible for one doctor to work with multiple working groups?
    title = models.CharField(max_length=4, blank=True, null=True)
    family_name = models.CharField(max_length=100, db_index=True, verbose_name="Family/Last name")
    given_names = models.CharField(max_length=100, db_index=True, verbose_name="Given/First names")
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True, null=True)
    surgery_name = models.CharField(max_length=100, blank=True)
    speciality = models.CharField(max_length=100)
    address = models.TextField()
    suburb = models.CharField(max_length=50, verbose_name="Suburb/Town/City")
    postcode = models.CharField(max_length=20, blank=True, null=True)
    state = models.ForeignKey(State, verbose_name="State/Province/Territory", blank=True, null=True,
                              on_delete=models.SET_NULL)
    phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    fax = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        ordering = ['family_name']

    def __str__(self):
        return "%s %s (%s)" % (self.family_name.upper(), self.given_names, self.surgery_name)


class NextOfKinRelationship(models.Model):
    relationship = models.CharField(max_length=100, verbose_name="Relationship")

    class Meta:
        verbose_name = 'Next of Kin Relationship'

    def __str__(self):
        return self.relationship


class PatientManager(models.Manager):

    def get_by_registry(self, *registries):
        return self.model.objects.filter(rdrf_registry__in=registries)

    def get_by_working_group(self, user):
        return self.model.objects.filter(working_groups__in=get_working_groups(user))

    def get_by_registry_and_working_group(self, registry, user):
        return self.model.objects.filter(rdrf_registry=registry, working_groups__in=get_working_groups(user))

    def get_filtered(self, user):
        return self.model.objects.filter(
            rdrf_registry__id__in=get_registries(user)).filter(
            working_groups__in=get_working_groups(user)).distinct()

    def get_filtered_unallocated(self, user):
        return self.model.objects.filter(
            working_groups__in=get_working_groups(user)).exclude(
            rdrf_registry__isnull=False)


class Patient(models.Model):

    SEX_CHOICES = (("1", "Male"), ("2", "Female"), ("3", "Indeterminate"))

    ETHNIC_ORIGIN = (
        ("New Zealand European", "New Zealand European"),
        ("Australian", "Australian"),
        ("Other Caucasian/European", "Other Caucasian/European"),
        ("Aboriginal", "Aboriginal"),
        ("Person from the Torres Strait Islands", "Person from the Torres Strait Islands"),
        ("Maori", "Maori"),
        ("NZ European / Maori", "NZ European / Maori"),
        ("Samoan", "Samoan"),
        ("Cook Islands Maori", "Cook Islands Maori"),
        ("Tongan", "Tongan"),
        ("Niuean", "Niuean"),
        ("Tokelauan", "Tokelauan"),
        ("Fijian", "Fijian"),
        ("Other Pacific Peoples", "Other Pacific Peoples"),
        ("Southeast Asian", "Southeast Asian"),
        ("Chinese", "Chinese"),
        ("Indian", "Indian"),
        ("Other Asian", "Other Asian"),
        ("Middle Eastern", "Middle Eastern"),
        ("Latin American", "Latin American"),
        ("Black African/African American", "Black African/African American"),
        ("Other Ethnicity", "Other Ethnicity"),
        ("Decline to Answer", "Decline to Answer"),
    )

    LIVING_STATES = (('Alive', 'Living'), ('Deceased', 'Deceased'))

    objects = PatientManager()
    rdrf_registry = models.ManyToManyField(Registry, related_name='patients')
    working_groups = models.ManyToManyField(
        registry.groups.models.WorkingGroup, related_name="my_patients", verbose_name="Centre")
    consent = models.BooleanField(
        null=False,
        blank=False,
        help_text="The patient consents to be part of the registry and have data retained and shared in accordance with the information provided to them.",
        verbose_name="consent given")
    consent_clinical_trials = models.BooleanField(
        null=False,
        blank=False,
        help_text="Consent given to be contacted about clinical trials or other studies related to their condition.",
        default=False)
    consent_sent_information = models.BooleanField(
        null=False,
        blank=False,
        help_text="Consent given to be sent information on their condition",
        verbose_name="consent to be sent information given",
        default=False)
    consent_provided_by_parent_guardian = models.BooleanField(
        null=False,
        blank=False,
        help_text="Parent/Guardian consent provided on behalf of the patient.",
        default=False)
    family_name = models.CharField(max_length=100, db_index=True)
    given_names = models.CharField(max_length=100, db_index=True)
    maiden_name = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Maiden name (if applicable)")
    umrn = models.CharField(
        max_length=50, null=True, blank=True, db_index=True, verbose_name="Hospital/Clinic ID")
    date_of_birth = models.DateField()
    place_of_birth = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Place of birth")
    country_of_birth = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Country of birth")
    ethnic_origin = models.CharField(
        choices=ETHNIC_ORIGIN, max_length=100, blank=True, null=True)
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    home_phone = models.CharField(max_length=30, blank=True, null=True)
    mobile_phone = models.CharField(max_length=30, blank=True, null=True)
    work_phone = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    next_of_kin_family_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="family name")
    next_of_kin_given_names = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="given names")
    next_of_kin_relationship = models.ForeignKey(
        NextOfKinRelationship,
        verbose_name="Relationship",
        blank=True,
        null=True,
        on_delete=models.SET_NULL)
    next_of_kin_address = models.TextField(blank=True, null=True, verbose_name="Address")
    next_of_kin_suburb = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Suburb/Town/City")
    next_of_kin_state = models.CharField(
        max_length=20, verbose_name="State/Province/Territory", blank=True, null=True)
    next_of_kin_postcode = models.IntegerField(verbose_name="Postcode", blank=True, null=True)
    next_of_kin_home_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="home phone")
    next_of_kin_mobile_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="mobile phone")
    next_of_kin_work_phone = models.CharField(
        max_length=30, blank=True, null=True, verbose_name="work phone")
    next_of_kin_email = models.EmailField(blank=True, null=True, verbose_name="email")
    next_of_kin_parent_place_of_birth = models.CharField(
        max_length=100, verbose_name="Place of birth of parents", blank=True, null=True)
    next_of_kin_country = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Country")
    doctors = models.ManyToManyField(Doctor, through="PatientDoctor")
    active = models.BooleanField(
        default=True,
        help_text="Ticked if active in the registry, ie not a deleted record, or deceased patient.")
    inactive_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Reason",
        help_text="Please provide reason for deactivating the patient")
    clinician = models.ForeignKey(CustomUser, blank=True, null=True)
    user = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        related_name="user_object",
        on_delete=models.SET_NULL)

    living_status = models.CharField(choices=LIVING_STATES, max_length=80, default='Alive')

    class Meta:
        ordering = ["family_name", "given_names", "date_of_birth"]
        verbose_name_plural = "Patient List"

        permissions = (
            ("can_see_full_name", "Can see Full Name column"),
            ("can_see_dob", "Can see Date of Birth column"),
            ("can_see_working_groups", "Can see Working Groups column"),
            ("can_see_diagnosis_progress", "Can see Diagnosis Progress column"),
            ("can_see_diagnosis_currency", "Can see Diagnosis Currency column"),
            ("can_see_genetic_data_map", "Can see Genetic Module column"),
            ("can_see_data_modules", "Can see Data Modules column"),
        )

    @property
    def display_name(self):
        if self.active:
            return "%s, %s" % (self.family_name, self.given_names)
        else:
            return "%s, %s (Archived)" % (self.family_name, self.given_names)

    @property
    def age(self):
        """ in years """
        from datetime import date

        def calculate_age(born):
            today = date.today()
            try:
                birthday = born.replace(year=today.year)
            # raised when birth date is February 29 and the current year is not a leap year
            except ValueError:
                birthday = born.replace(year=today.year, month=born.month + 1, day=1)
            if birthday > today:
                return today.year - born.year - 1
            else:
                return today.year - born.year

        try:
            age_in_years = calculate_age(self.date_of_birth)
            return age_in_years
        except:
            return None

    def has_feature(self, feature):
        return any([r.has_feature(feature) for r in self.rdrf_registry.all()])

    @property
    def working_groups_display(self):
        return ",".join([wg.display_name for wg in self.working_groups.all()])

    def clinical_data_currency(self, days=365):
        """
        If some clinical form ( non genetic ) has been updated  in the window
        then the data for that registry is considered "current" - this mirrors
        """
        time_window_start = datetime.datetime.now() - datetime.timedelta(days=days)
        currency_map = {}
        for registry_model in self.rdrf_registry.all():
            last_updated_in_window = False
            for form_model in registry_model.forms:
                if "genetic" in form_model.name.lower():
                    continue
                form_timestamp = self.get_form_timestamp(form_model)
                logger.debug("form timestamp %s = %s" % (form_model, form_timestamp))
                if form_timestamp and form_timestamp >= time_window_start:
                    last_updated_in_window = True
                    break
            currency_map[registry_model.code] = last_updated_in_window

        return currency_map

    @property
    def genetic_data_map(self):
        """
        map of reg code to Boolean iff patient has some genetic data filled in
        """
        registry_genetic_progress = {}

        class Sentinel(Exception):
            pass

        for registry_model in self.rdrf_registry.all():
            has_data = False
            try:
                for form_model in registry_model.forms:
                    if "genetic" in form_model.name.lower():
                        for section_model in form_model.section_models:
                            for cde_model in section_model.cde_models:
                                try:
                                    value = self.get_form_value(registry_model.code,
                                                                form_model.name,
                                                                section_model.code,
                                                                cde_model.code,
                                                                section_model.allow_multiple)

                                    # got value for at least one field
                                    raise Sentinel()
                                except KeyError:
                                    pass
            except Sentinel:
                has_data = True

            registry_genetic_progress[registry_model.code] = has_data
        return registry_genetic_progress

    def get_form_value(
            self,
            registry_code,
            form_name,
            section_code,
            data_element_code,
            multisection=False,
            context_id=None):
        from rdrf.dynamic_data import DynamicDataWrapper
        from rdrf.utils import mongo_key
        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_id)
        mongo_data = wrapper.load_dynamic_data(registry_code, "cdes")
        key = mongo_key(form_name, section_code, data_element_code)
        if mongo_data is None:
            # no mongo data
            raise KeyError(key)
        else:
            if multisection:
                sections = mongo_data[section_code]
                values = []
                for section in sections:
                    if key in section and section[key]:
                        values.append(section[key])
                return values
            else:
                return mongo_data[key]

    def update_field_expressions(self, registry_model, field_expressions, context_model=None):
        from rdrf.dynamic_data import DynamicDataWrapper
        from rdrf.generalised_field_expressions import GeneralisedFieldExpressionParser
        if registry_model.has_feature("contexts") and context_model is None:
            raise Exception("No context model set")
        elif not registry_model.has_feature("contexts") and context_model is not None:
            raise Exception("context model should not be explicit for non-supporting registry")
        elif not registry_model.has_feature("contexts") and context_model is None:
            # the usual case
            from rdrf.contexts_api import RDRFContextManager
            rdrf_context_manager = RDRFContextManager(registry_model)
            context_model = rdrf_context_manager.get_or_create_default_context(self)

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_model.pk)
        parser = GeneralisedFieldExpressionParser(registry_model)
        mongo_data = wrapper.load_dynamic_data(registry_model.code, "cdes", flattened=False)

        logger.debug("updating field expressions ...")
        errors = 0
        error_messages = []
        succeeded = 0
        total = 0

        for field_expression, new_value in field_expressions:
            logger.debug("errors = %s" % errors)
            logger.debug("succeeded = %s" % succeeded)
            logger.debug("total = %s" % total)

            logger.debug("%%%%%%%% updating field %s" % field_expression)

            total += 1
            try:
                expression_object = parser.parse(field_expression)
                logger.debug("parsed %s OK: is a %s" % (field_expression,
                                                        expression_object.__class__.__name__))
            except Exception as ex:
                errors += 1
                logger.debug("couldn't parse field expression: %s - skipping" % field_expression)
                error_messages.append("Parse error: %s" % field_expression)
                continue

            try:
                logger.debug("attempting to update %s --> %s" % (field_expression, new_value))
                self, mongo_data = expression_object.set_value(self, mongo_data, new_value, context_id=context_model.pk)
                logger.debug("%s --> %s OK!" % (field_expression, new_value))
                succeeded += 1
            except NotImplementedError:
                errors += 1
                logger.debug("need to implement %s - skipping" % field_expression)
                error_messages.append("Not Implemented: %s" % field_expression)
                continue

            except Exception as ex:
                errors += 1
                logger.debug("Erroring setting value for field_expression %s: %s" % (field_expression, ex))
                error_messages.append("Error setting value for %s: %s" % (field_expression, ex))

        logger.debug("errors = %s" % errors)
        logger.debug("succeeded = %s" % succeeded)
        logger.debug("total = %s" % total)

        try:
            wrapper.update_dynamic_data(registry_model, mongo_data)
        except Exception as ex:
            logger.error("Error update_dynamic_data: %s" % ex)
            error_messages.append("Failed to update: %s" % ex)
        try:
            self.save()
        except Exception as ex:
            error_messages.append("Failed to save patient: %s" % ex)

        return error_messages

    def evaluate_field_expression(self, registry_model, field_expression, **kwargs):
        if "value" in kwargs:
            setting_value = True
            value = kwargs["value"]
        else:
            setting_value = False

        # TODO need to support contexts - supply in kwargs
        context_model = self.default_context(registry_model)

        from rdrf.generalised_field_expressions import GeneralisedFieldExpressionParser
        parser = GeneralisedFieldExpressionParser(registry_model)

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_model.pk)
        mongo_data = wrapper.load_dynamic_data(registry_model.code, "cdes", flattened=False)

        if mongo_data is None:
            # ensure we have sane data frame
            mongo_data = {"django_id": self.pk,
                          "django_model": "Patient",
                          "timestamp":  datetime.datetime.now(),
                          "context_id": context_model.pk,
                          "forms": []}

        if not setting_value:
            # ie retrieving a value
            # or doing an action like clearing a multisection
            action = parser.parse(field_expression)
            return action(self, mongo_data)
        else:
            setter = parser.parse(field_expression)
            # operate on patient_model supplying value
            # gfe's operate on either sql or mongo
            patient_model, mongo_data = setter.set_value(self, mongo_data, value)
            patient_model.save()
            return wrapper.update_dynamic_data(registry_model, mongo_data)

    def set_form_value(self, registry_code, form_name, section_code, data_element_code, value, context_model=None):
        from rdrf.dynamic_data import DynamicDataWrapper
        from rdrf.utils import mongo_key
        from rdrf.form_progress import FormProgress
        from rdrf.models import RegistryForm, Registry
        registry_model = Registry.objects.get(code=registry_code)
        if registry_model.has_feature("contexts") and context_model is None:
            raise Exception("No context model set")
        elif not registry_model.has_feature("contexts") and context_model is not None:
            raise Exception("context model should not be explicit for non-supporting registry")
        elif not registry_model.has_feature("contexts") and context_model is None:
            # the usual case
            from rdrf.contexts_api import RDRFContextManager
            rdrf_context_manager = RDRFContextManager(registry_model)
            context_model = rdrf_context_manager.get_or_create_default_context(self)

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_model.pk)

        form_model = RegistryForm(name=form_name, registry=registry_model)
        wrapper.current_form_model = form_model

        mongo_data = wrapper.load_dynamic_data(registry_code, "cdes")
        key = mongo_key(form_name, section_code, data_element_code)
        timestamp = "%s_timestamp" % form_name
        t = datetime.datetime.now()

        if mongo_data is None:
            # No dynamic data has been persisted yet
            wrapper.save_dynamic_data(registry_code, "cdes", {key: value, timestamp: t})
        else:
            mongo_data[key] = value
            mongo_data[timestamp] = t
            wrapper.save_dynamic_data(registry_code, "cdes", mongo_data)

        # update form progress
        registry_model = Registry.objects.get(code=registry_code)
        form_progress_calculator = FormProgress(registry_model)
        form_progress_calculator.save_for_patient(self, context_model)

    def in_registry(self, reg_code):
        """
        returns True if patient belongs to the registry with reg code provided
        """
        for registry in self.rdrf_registry.all():
            if registry.code == reg_code:
                return True

    @property
    def my_index(self):
        logger.debug("Finding index of %s" % self)
        # This property is only applicable to FH
        if self.in_registry("fh"):
            # try to find patient relative object corresponding to this patient and
            # then locate that relative's index patient
            logger.debug("patient is in FH so this makes sense")
            try:
                patient_relative = PatientRelative.objects.get(relative_patient=self)
                logger.debug("There is a PatientRelative I was created from: %s" % patient_relative)
                if patient_relative.patient:
                    logger.debug("This patient relative has a patient property: index = %s" % patient_relative.patient)
                    return patient_relative.patient
                else:
                    logger.debug("PatientRelative %s has no patient property (is null)" % patient_relative)
                    return None
            except PatientRelative.DoesNotExist:
                logger.debug("no patient relative exists for %s so my index is None" % self)
                return None

        logger.debug("%s not in FH - so my_index is None" % self)

        return None

    def get_contexts_url(self, registry_model):
        # TODO - change so we don't need this
        return None
        if not registry_model.has_feature("contexts"):
            return None
        else:
            base_url = reverse("contextslisting")
            full_url = "%s?registry_code=%s&patient_id=%s" % (base_url,
                                                              registry_model.code,
                                                              self.pk)
            return full_url

    def sync_patient_relative(self):
        logger.debug("Attempting to sync PatientRelative")
        # If there is a patient relative ( from which I was created)
        # then synchronise my common properties:
        try:
            pr = PatientRelative.objects.get(relative_patient=self)
        except PatientRelative.DoesNotExist:
            logger.debug("no PatientRelative to sync")
            return
        logger.debug("Patient %s updating PatientRelative %s" % (self, pr))
        pr.given_names = self.given_names
        pr.family_name = self.family_name
        pr.date_of_birth = self.date_of_birth
        pr.sex = self.sex
        pr.living_status = self.living_status
        pr.save()
        logger.debug("synced PatientRelative OK")

    def set_consent(self, consent_model, answer=True, commit=True):
        patient_registries = [r for r in self.rdrf_registry.all()]
        if consent_model.section.registry not in patient_registries:
            return   # error?
        cv, created = ConsentValue.objects.get_or_create(
            consent_question=consent_model, patient=self)
        cv.answer = answer
        if cv.first_save:
            cv.last_update = datetime.datetime.now()
        else:
            cv.first_save = datetime.datetime.now()
        if commit:
            cv.save()
        return cv

    def get_consent(self, consent_model, field="answer"):
        patient_registries = [r for r in self.rdrf_registry.all()]
        if consent_model.section.registry not in patient_registries:
            if field == "answer":
                return False    # ?
            else:
                logger.debug("consent model not in patient registries")
                return None
        try:
            cv = ConsentValue.objects.get(patient=self, consent_question=consent_model)
            if field == "answer":
                return cv.answer
            elif field == "first_save":
                return cv.first_save
            elif field == "last_update":
                return cv.last_update
            else:
                raise ValueError("only consent_value answer, first_save, last_update fields allowed")

        except ConsentValue.DoesNotExist:
            if field == "answer":
                return False    # ?
            else:
                return None

    @property
    def consent_questions_data(self):
        d = {}
        for consent_value in ConsentValue.objects.filter(patient=self):
            consent_question_model = consent_value.consent_question
            d[consent_question_model.field_key] = consent_value.answer
        return d

    def clean_consents(self):
        my_registries = [r for r in self.rdrf_registry.all()]
        for consent_value in ConsentValue.objects.filter(patient=self):
            if consent_value.consent_question.section.registry not in my_registries:
                consent_value.delete()

    @property
    def is_index(self):
        if not self.active:
            return False

        if not self.in_registry("fh"):
            return False
        else:
            if not self.my_index:
                return True
            else:
                return False

    @property
    def has_guardian(self):
        return ParentGuardian.objects.filter(patient=self).count() > 0

    @property
    def combined_name(self):
        if self.has_guardian:
            guardians = [pg for pg in ParentGuardian.objects.filter(patient=self)]
            g = guardians[0]
            name = "%s on behalf of %s" % (g, self)
            return name
        else:
            return "%s" % self

    def __str__(self):
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

    def form_progress(self, registry_form, numbers_only=False):
        if not registry_form.has_progress_indicator:
            if numbers_only:
                return 0, 0

            return [], 0

        required = 0
        set_count = 0
        cdes_status = {}
        registry_model = registry_form.registry
        registry_code = registry_model.code
        cde_codes_required = [cde.code for cde in registry_form.complete_form_cdes.all()]
        for section_model in registry_form.section_models:
            for cde_model in section_model.cde_models:
                if cde_model.code in cde_codes_required:
                    required += 1
                    try:
                        cde_value = self.get_form_value(registry_code,
                                                        registry_form.name,
                                                        section_model.code,
                                                        cde_model.code,
                                                        section_model.allow_multiple)
                    except KeyError:
                        cde_value = None

                    cdes_status[cde_model.name] = False
                    if cde_value:
                        cdes_status[cde_model.name] = True
                        set_count += 1

        if numbers_only:
            return set_count, required

        try:
            percentage = float(set_count) / float(required) * 100
        except ZeroDivisionError:
            percentage = 0

        return cdes_status, percentage

    def forms_progress(self, registry_model, forms):
        from rdrf.utils import mongo_key
        mongo_data = DynamicDataWrapper(self).load_dynamic_data(registry_model.code, "cdes")
        total_filled_in = 0
        total_required_for_completion = 0

        for registry_form in forms:
            if not registry_form.has_progress_indicator:
                continue

            section_array = registry_form.sections.split(",")

            cde_complete = list(registry_form.complete_form_cdes.values())
            total_required_for_completion += len(registry_form.complete_form_cdes.values_list())

            for cde in cde_complete:
                cde_section = ""
                for s in section_array:
                    section = Section.objects.get(code=s)
                    if cde["code"] in section.elements.split(","):
                        cde_section = s
                try:
                    cde_key = mongo_key(registry_form.name, cde_section, cde["code"])
                    cde_value = mongo_data[cde_key]
                except KeyError:
                    cde_value = None

                if cde_value:
                    total_filled_in += 1

        return total_filled_in, total_required_for_completion

    def get_form_timestamp(self, registry_form):
        dynamic_store = DynamicDataWrapper(self)
        timestamp = dynamic_store.get_form_timestamp(registry_form)
        if timestamp:
            if "timestamp" in timestamp:
                ts = timestamp["timestamp"]
                return ts

    def form_currency(self, registry_form):
        dynamic_store = DynamicDataWrapper(self)
        timestamp = dynamic_store.get_form_timestamp(registry_form)
        if timestamp:
            if "timestamp" in timestamp:
                ts = timestamp["timestamp"]
                delta = datetime.datetime.now() - ts
                return True if delta.days < _6MONTHS_IN_DAYS else False
            else:
                return True
        else:
            return False

    def as_json(self):
        return dict(
            obj_id=self.id,
            given_names=self.given_names,
            family_name=self.family_name,
            working_group=self.working_group.name,
            date_of_birth=str(self.date_of_birth)
        )

    @property
    def context_models(self):
        from django.contrib.contenttypes.models import ContentType
        from rdrf.models import RDRFContext
        contexts = []
        content_type = ContentType.objects.get_for_model(self)

        for context_model in RDRFContext.objects.filter(content_type=content_type,
                                                        object_id=self.pk).order_by("created_at"):
            contexts.append(context_model)
        return contexts

    def get_forms_by_group(self, context_form_group):
        """
        Return links (pair of url and text)
        to existing forms "of type" (ie being in a context with a link to)  context_form_group

        """
        assert context_form_group.supports_direct_linking, "Context Form group must only contain one form"

        form_model = context_form_group.form_models[0]

        links = []

        for context_model in sorted(self.context_models, key=lambda c: c.created_at, reverse=True):
            if context_model.context_form_group and context_model.context_form_group.pk == context_form_group.pk:
                link_text = context_model.context_form_group.get_name_from_cde(self, context_model)
                link_url = reverse('registry_form', args=(context_model.registry.code,
                                                          form_model.id,
                                                          self.pk,
                                                          context_model.id))
                links.append((link_url, link_text))

        return links

    def default_context(self, registry_model):
        # return None if doesn't make sense
        from rdrf.models import RegistryType
        registry_type = registry_model.registry_type
        if registry_type == RegistryType.NORMAL:
            my_contexts = self.context_models
            num_contexts = len(my_contexts)
            if num_contexts == 1:
                return my_contexts[0]
            else:
                raise Exception("default context could not be returned: num contexts = %s" % num_contexts)

        elif registry_type == RegistryType.HAS_CONTEXTS:
            return None
        else:
            # registry has context form groups defined
            for context_model in self.context_models:
                if context_model.context_form_group:
                    if context_model.context_form_group.is_default:
                        return context_model
            raise Exception("no default context")

    def get_dynamic_data(self, registry_model, collection="cdes", context_id=None):
        from rdrf.dynamic_data import DynamicDataWrapper
        logger.debug("in get_dynamic_data")
        if context_id is None:
            default_context = self.default_context(registry_model)
            if default_context is not None:
                context_id = default_context.pk
            else:
                raise Exception("need context id to get dynamic data for patient %s" % self.pk)

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_id)

        return wrapper.load_dynamic_data(registry_model.code, collection, flattened=False)

    def update_dynamic_data(self, registry_model, new_mongo_data, context_id=None):
        """
        Completely replace a patient's mongo record
        Dangerous - assumes new_mongo_data is correct structure
        Trying it to simulate rollback if questionnaire update fails
        """
        from rdrf.dynamic_data import DynamicDataWrapper
        if context_id is None:
            default_context = self.default_context(registry_model)
            if default_context is not None:
                context_id = default_context.pk
            else:
                raise Exception("need context id to get update dynamic data for patient %s" % self.pk)

        wrapper = DynamicDataWrapper(self, rdrf_context_id=context_id)
        # NB warning this completely replaces the existing mongo record for the patient
        # useful for "rolling back" after questionnaire update failure
        logger.info("Warning! : Updating existing dynamic data for %s(%s) in registry %s" % (self,
                                                                                             self.pk,
                                                                                             registry_model))
        logger.info("New Mongo data record = %s" % new_mongo_data)
        if new_mongo_data is not None:
            wrapper.update_dynamic_data(registry_model, new_mongo_data)
        else:
            # this means we want to delete the existing incorrect questionnaire data
            # and go back to before the update when the patient had no data in mongo
            logger.info("New data is None so the existing record will be deleted")
            logger.info("deleting record for patient %s registry %s context %s" % (self.pk,
                                                                                   registry_model,
                                                                                   context_id))
            wrapper.delete_patient_record(registry_model, context_id)


class ClinicianOther(models.Model):
    patient = models.ForeignKey(Patient, null=True)
    clinician_name = models.CharField(max_length=200, null=True)
    clinician_hospital = models.CharField(max_length=200, null=True)
    clinician_address = models.CharField(max_length=200, null=True)
    clinician_email = models.EmailField(max_length=254, null=True, blank=True)
    clinician_phone_number = models.CharField(max_length=254, null=True, blank=True)


class ParentGuardian(models.Model):
    GENDER_CHOICES = (("1", "Male"), ("2", "Female"), ("3", "Indeterminate"))

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(blank=True, null=True)
    place_of_birth = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Place of birth")
    date_of_migration = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    address = models.TextField()
    suburb = models.CharField(max_length=50, verbose_name="Suburb/Town")
    state = models.CharField(max_length=20, verbose_name="State/Province/Territory")
    postcode = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)
    patient = models.ManyToManyField(Patient)
    self_patient = models.ForeignKey(
        Patient, blank=True, null=True, related_name="self_patient")
    user = models.ForeignKey(
        CustomUser,
        blank=True,
        null=True,
        related_name="parent_user_object",
        on_delete=models.SET_NULL)

@receiver(post_save, sender=ParentGuardian)
def update_my_user(sender, **kwargs):
    """
    Propagate name change on parent to user if they
    have one.
    """
    parent_guardian = kwargs["instance"]
    user = parent_guardian.user
    if user:
        user.first_name = parent_guardian.first_name
        user.last_name = parent_guardian.last_name
        user.save()

class AddressTypeManager(models.Manager):

    def get_by_natural_key(self, type):
        return self.get(type=type)


class AddressType(models.Model):
    objects = AddressTypeManager()

    type = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)

    def natural_key(self):
        return (self.type,)

    def __str__(self):
        return "%s" % (self.type)


class PatientAddress(models.Model):
    patient = models.ForeignKey(Patient)
    address_type = models.ForeignKey(AddressType, default=1)
    address = models.TextField()
    suburb = models.CharField(max_length=100, verbose_name="Suburb/Town")
    state = models.CharField(max_length=50, verbose_name="State/Province/Territory")
    postcode = models.CharField(max_length=50)
    country = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Patient Addresses"

    def __str__(self):
        return ""


class PatientConsentStorage(DefaultStorage):
    """
    This is a normal default file storage, except the URL points to
    authenticated file download view.
    """

    def url(self, name):
        consent = PatientConsent.objects.filter(form=name).first()
        if consent is not None:
            rev = dict(consent_id=consent.id, filename=consent.filename)
            return reverse("registry:consent-form-download", kwargs=rev)
        return None


class PatientConsent(models.Model):
    patient = models.ForeignKey(Patient)
    form = models.FileField(
        upload_to='consents',
        storage=PatientConsentStorage(),
        verbose_name="Consent form",
        blank=True,
        null=True)
    filename = models.CharField(max_length=255)


class PatientDoctor(models.Model):
    patient = models.ForeignKey(Patient)
    doctor = models.ForeignKey(Doctor)
    relationship = models.CharField(max_length=50)

    class Meta:
        verbose_name = "medical professionals for patient"
        verbose_name_plural = "medical professionals for patient"


def get_countries():
    return [(c.alpha2, c.name)
            for c in sorted(pycountry.countries, key=attrgetter("name"))]


class PatientRelative(models.Model):

    RELATIVE_TYPES = (("Parent (1st degree)", "Parent (1st degree)"),
                      ("Child (1st degree)", "Child (1st degree)"),
                      ("Sibling (1st degree)", "Sibling (1st degree)"),
                      ("Identical Twin (0th degree)", "Identical Twin (0th degree)"),
                      ("Non-identical Twin (1st degree)", "Non-identical Twin (1st degree)"),
                      ("Half Sibling (1st degree)", "Half Sibling (1st degree)"),
                      ("Grandparent (2nd degree)", "Grandparent (2nd degree)"),
                      ("Grandchild (2nd degree)", "Grandchild (2nd degree)"),
                      ("Uncle/Aunt (2nd degree)", "Uncle/Aunt (2nd degree)"),
                      ("Niece/Nephew (2nd degree)", "Niece/Nephew (2nd degree)"),
                      ("1st Cousin (3rd degree)", "1st Cousin (3rd degree)"),
                      ("Great Grandparent (3rd degree)", "Great Grandparent (3rd degree)"),
                      ("Great Grandchild (3rd degree)", "Great Grandchild (3rd degree)"),
                      ("Great Uncle/Aunt (3rd degree)", "Great Uncle/Aunt (3rd degree)"),
                      ("Grand Niece/Nephew (3rd degree)", "Grand Niece/Nephew (3rd degree)"),
                      ("1st Cousin once removed (4th degree)", "1st Cousin once removed (4th degree)"),
                      ("Spouse", "Spouse"),
                      ("Unknown", "Unknown"),
                      ("Other", "Other"),
                      )

    RELATIVE_LOCATIONS = [
        ("AU - WA", "Australia - WA"),
        ("AU - SA", "Australia - SA"),
        ("AU - NSW", "Australia - NSW"),
        ("AU - QLD", "Australia - QLD"),
        ("AU - NT", "Australia - NT"),
        ("AU - VIC", "Australia - VIC"),
        ("AU - TAS", "Australia - TAS"),
        ("NZ", "New Zealand")

    ]

    LIVING_STATES = (('Alive', 'Living'), ('Deceased', 'Deceased'))

    SEX_CHOICES = (("1", "Male"), ("2", "Female"), ("3", "Indeterminate"))
    patient = models.ForeignKey(Patient, related_name="relatives")
    family_name = models.CharField(max_length=100)
    given_names = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    sex = models.CharField(max_length=1, choices=SEX_CHOICES)
    relationship = models.CharField(choices=RELATIVE_TYPES, max_length=80)
    location = models.CharField(choices=RELATIVE_LOCATIONS + get_countries(), max_length=80)
    living_status = models.CharField(choices=LIVING_STATES, max_length=80)
    relative_patient = models.OneToOneField(
        to=Patient,
        null=True,
        blank=True,
        related_name="as_a_relative",
        verbose_name="Create Patient?")

    def create_patient_from_myself(self, registry_model, working_groups):
        # Create the patient corresponding to this relative
        logger.debug("creating a patient model from patient relative %s ..." % self)
        p = Patient()
        p.given_names = self.given_names
        p.family_name = self.family_name
        p.date_of_birth = self.date_of_birth
        p.sex = self.sex
        p.consent = True   # tricky ?
        p.active = True
        p.living_status = self.living_status

        try:
            p.save()
        except Exception as ex:
            raise ValidationError("Could not create patient from relative: %s" % ex)

        p.rdrf_registry = [registry_model]
        p.working_groups = working_groups
        p.save()
        logger.debug("saved created patient ok with pk = %s" % p.pk)
        run_hooks('patient_created_from_relative', p)
        logger.debug("ran hooks ok")

        # set the patient relative model relative_patient field to point to this
        # newly created patient
        self.relative_patient = p
        self.save()
        logger.debug("updated %s relative_patient to %s" % (self, p))
        return p

    def sync_relative_patient(self):
        if self.relative_patient:
            self.relative_patient.given_names = self.given_names
            self.relative_patient.family_name = self.family_name
            self.relative_patient.date_of_birth = self.date_of_birth
            self.relative_patient.sex = self.sex
            self.relative_patient.living_status = self.living_status
            self.relative_patient.save()


@receiver(post_delete, sender=PatientRelative)
def delete_created_patient(sender, instance, **kwargs):
    if instance.relative_patient:
        #  when doing family linkage operation of moving
        #  a relative to an index , we were seeing this
        #  signal archive the newly "promoted" relative's patient
        #  so don't do this!
        if not instance.relative_patient.is_index:
            if not hasattr(instance, "skip_archiving"):
                instance.relative_patient.delete()


@receiver(post_save, sender=Patient)
def clean_consents(sender, instance, **kwargs):
    instance.clean_consents()


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


@receiver(post_save, sender=Patient)
def save_patient_hooks(sender, instance, created, **kwargs):
    if created:
        run_hooks('patient_created', instance)
    else:
        run_hooks('existing_patient_saved', instance)


@receiver(m2m_changed, sender=Patient.rdrf_registry.through)
def registry_changed_on_patient(sender, **kwargs):
    logger.debug("registry changed on patient %s: kwargs = %s" % (kwargs['instance'], kwargs))
    if kwargs["action"] == "post_add":
        from rdrf.contexts_api import create_rdrf_default_contexts
        instance = kwargs['instance']
        registry_ids = kwargs['pk_set']
        create_rdrf_default_contexts(instance, registry_ids)
        run_hooks('registry_added', instance, registry_ids)


class ConsentValue(models.Model):
    patient = models.ForeignKey(Patient, related_name="consents")
    consent_question = models.ForeignKey(ConsentQuestion)
    answer = models.BooleanField(default=False)
    first_save = models.DateField(null=True, blank=True)
    last_update = models.DateField(null=True, blank=True)

    def __str__(self):
        return "Consent Value for %s question %s is %s" % (
            self.patient, self.consent_question, self.answer)


@receiver(post_delete, sender=PatientRelative)
def delete_associated_patient_if_any(sender, instance, **kwargs):
    logger.debug("post_delete of patient relative")
    logger.debug("instance = %s" % instance)
    logger.debug("sender = %s kwargs = %s" % (sender, kwargs))
    if instance.relative_patient:
        logger.debug("about to delete patient created from relative: %s" % instance.relative_patient)
        if not hasattr(instance, "skip_archiving"):
            logger.debug("no skip_archiving attribute so deleting the PatientRelative.relative_patient")
            instance.relative_patient.delete()
        else:
            logger.debug("skip_archiving is set on PatientRelative so won't archive")
