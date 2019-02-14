from django.conf.urls import url
from django.contrib import admin
from django.db.models import Q
from django.http import HttpResponse
from django.urls import reverse
import os
import json
import datetime
from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import ClinicalData
from registry.utils import get_static_url
from registry.utils import get_working_groups
from .admin_forms import (
    PatientForm,
    PatientAddressForm,
    PatientDoctorForm,
    PatientRelativeForm)
from .models import (
    AddressType,
    ClinicianOther,
    ParentGuardian,
    Doctor,
    State,
    Patient,
    PatientAddress,
    PatientDoctor,
    PatientRelative,
    PatientConsent,
    NextOfKinRelationship)
from rdrf.db.dynamic_data import DynamicDataWrapper
from django.contrib.auth import get_user_model
import logging
from registry.patients.models import ConsentValue

logger = logging.getLogger(__name__)


class DoctorAdmin(admin.ModelAdmin):
    search_fields = ["family_name", "given_names"]


class PatientDoctorAdmin(admin.TabularInline):
    fields = ["relationship", "doctor"]
    form = PatientDoctorForm
    model = PatientDoctor
    extra = 0


class PatientRelativeAdmin(admin.TabularInline):
    model = PatientRelative
    form = PatientRelativeForm
    fk_name = 'patient'
    extra = 1


class PatientConsentAdmin(admin.TabularInline):
    model = PatientConsent
    extra = 1


class PatientAddressAdmin(admin.StackedInline):
    model = PatientAddress
    form = PatientAddressForm
    extra = 0


class RegistryFilter(admin.SimpleListFilter):
    title = "Registry"
    parameter_name = 'registry'

    def lookups(self, request, model_admin):

        if request.user.is_superuser:
            reg_list = Registry.objects.all()
        else:
            reg_list = get_user_model().objects.get(username=request.user).registry.all()

        regs = []
        for reg in reg_list:
            regs.append((reg.id, reg.name))

        return regs

    def queryset(self, request, queryset):
        if request.GET.__contains__('registry'):
            reg = request.GET.__getitem__('registry')
            return queryset.filter(rdrf_registry__id__exact=reg)

        return queryset


class PatientAdmin(admin.ModelAdmin):

    def __init__(self, *args, **kwargs):
        super(PatientAdmin, self).__init__(*args, **kwargs)
        self.list_display_links = None

    app_url = os.environ.get("SCRIPT_NAME", "")
    form = PatientForm
    request = None

    inlines = [PatientAddressAdmin, PatientConsentAdmin,
               PatientDoctorAdmin, PatientRelativeAdmin]
    search_fields = ["family_name", "given_names"]
    list_display = ['full_name', 'working_groups_display', 'get_reg_list',
                    'date_of_birth', 'demographic_btn']

    list_filter = [RegistryFilter]

    def full_name(self, obj):
        return str(obj)

    full_name.short_description = 'Name'

    def demographic_btn(self, obj):
        return "<a href='%s' class='btn btn-info btn-small'>Details</a>" % reverse(
            'admin:patients_patient_change',
            args=(
                obj.id,
            ))

    demographic_btn.allow_tags = True
    demographic_btn.short_description = 'Demographics'

    def get_form(self, request, obj=None, **kwargs):
        """
        PatientAdmin.get_form
        :param request:
        :param obj:
        :param kwargs:
        :return:
        """
        # NB. This method returns a form class
        user = get_user_model().objects.get(username=request.user)
        # registry_specific_fields = self._get_registry_specific_patient_fields(user)
        # self.form = self._add_registry_specific_fields(self.form, registry_specific_fields)
        form = super(PatientAdmin, self).get_form(request, obj, **kwargs)
        form.user = user
        form.is_superuser = request.user.is_superuser
        return form

    def render_change_form(self, *args, **kwargs):
        # return self.render_change_form(request, context, change=True, obj=obj,
        # form_url=form_url)
        request = args[0]
        user = request.user
        context = args[1]
        if 'original' in context:
            patient = context['original']
            context['form_links'] = self._get_formlinks(patient, user)
        return super(PatientAdmin, self).render_change_form(*args, **kwargs)

    def _get_formlinks(self, patient, user):
        from rdrf.helpers.utils import FormLink
        links = []
        for registry_model in patient.rdrf_registry.all():
            for form_model in registry_model.forms:
                if form_model.is_questionnaire or not user.can_view(form_model):
                    continue
                form_link = FormLink(patient.id, registry_model, form_model)
                links.append(form_link)
        return links

    def _add_registry_specific_fields(self, form_class, registry_specific_fields_dict):
        additional_fields = {}
        for reg_code in registry_specific_fields_dict:
            field_pairs = registry_specific_fields_dict[reg_code]
            for cde, field_object in field_pairs:
                additional_fields[cde.code] = field_object

        new_form_class = type(form_class.__name__, (form_class,), additional_fields)
        return new_form_class

    def _get_registry_specific_patient_fields(self, user):
        """
        :param user:
        :return: a dictionary mapping registry codes to lists of pairs of cde models and field objects
        """
        result_dict = {}
        for registry in user.registry.all():
            patient_cde_field_pairs = registry.patient_fields
            if patient_cde_field_pairs:
                result_dict[registry.code] = patient_cde_field_pairs

        return result_dict

    def _get_registry_specific_fieldsets(self, user):
        reg_spec_field_defs = self._get_registry_specific_patient_fields(user)
        fieldsets = []
        for reg_code in reg_spec_field_defs:
            cde_field_pairs = reversed(reg_spec_field_defs[reg_code])
            fieldset_title = "%s Specific Fields" % reg_code.upper()
            # pair up cde name and field object generated from that cde
            field_dict = {"fields": [pair[0].code for pair in cde_field_pairs]}
            fieldsets.append((fieldset_title, field_dict))
        return fieldsets

    def create_fieldset(self, user):

        consent = ("Consent", {
            "fields": (
                "consent",
                "consent_provided_by_parent_guardian",
                "consent_clinical_trials",
                "consent_sent_information",

            )
        })

        rdrf_registry = ("Registry", {
            "fields": (
                "rdrf_registry",
                "clinician"
            )
        })

        personal_details = ("Personal Details", {})

        personal_details_fields = [
            "working_groups",
            "family_name",
            "given_names",
            "maiden_name",
            "umrn",
            "date_of_birth",
            "place_of_birth",
            "country_of_birth",
            "ethnic_origin",
            "sex",
            "home_phone",
            "mobile_phone",
            "work_phone",
            "email"
        ]

        # fix for Trac #3, the field is now always displayed, but readonly for not
        # superuser users, see get_readonly_fields below
        personal_details_fields.append("active")
        personal_details_fields.append("inactive_reason")

        personal_details[1]["fields"] = tuple(personal_details_fields)

        next_of_kin = ("Next of Kin", {
            "fields":
            ("next_of_kin_family_name",
             "next_of_kin_given_names",
             "next_of_kin_relationship",
             "next_of_kin_address",
             "next_of_kin_country",
             "next_of_kin_suburb",
             "next_of_kin_state",
             "next_of_kin_postcode",
             "next_of_kin_home_phone",
             "next_of_kin_mobile_phone",
             "next_of_kin_work_phone",
             "next_of_kin_email",
             "next_of_kin_parent_place_of_birth"
             )})

        fieldset = [consent, rdrf_registry, personal_details, next_of_kin]
        # fieldset.extend(self._get_registry_specific_section_fields(user))
        return fieldset

    def save_form(self, request, form, change):
        """
        We override save_form to support saving (some) registry specific data to Mongo
        The wrinkle is that the instance has not yet been saved, so if the user is adding a patient
        there will be no primary key ( all mongo data is linked to django via a primary key). We work around tbis, by tagging the data to be saved in Mongo
        on the instance and overriding save_model ( see below )
        """
        mongo_patient_data = {}
        instance = form.save(commit=False)
        if mongo_patient_data:
            instance.mongo_patient_data = mongo_patient_data

        return instance

    def save_model(self, request, obj, form, change):
        """
        Override ModelAdmin code to allow us to save the registry specific patient to Mongo ...
        """
        obj.save()

        if hasattr(obj, 'mongo_patient_data'):
            self._save_registry_specific_data_in_mongo(obj)

    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        if formset.__class__.__name__ == 'PatientRelativeFormFormSet':
            # check to see if we're creating a patient from this relative
            formset.save()
        else:
            formset.save()

    def get_fieldsets(self, request, obj=None):
        return self.create_fieldset(request.user)

    def _save_registry_specific_data_in_mongo(self, patient):
        data = patient.mongo_patient_data
        mongo_wrapper = DynamicDataWrapper(patient)
        mongo_wrapper.save_registry_specific_data(data)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []
        else:
            # return ['active'] # NB this seems to run into a mango bug that prevents
            # Add Patient being used by non-superuser
            return []

    def formfield_for_dbfield(self, dbfield, *args, **kwargs):
        from registry.groups.models import WorkingGroup

        request = kwargs.get('request')
        user = request.user
        # Restrict normal users to their own working group.
        if dbfield.name == "working_groups" and not user.is_superuser:
            # get the user's associated objects
            user = get_user_model().objects.get(username=user)
            kwargs["queryset"] = WorkingGroup.objects.filter(id__in=get_working_groups(user))

        if dbfield.name == "rdrf_registry" and not user.is_superuser:
            user = get_user_model().objects.get(username=user)
            kwargs["queryset"] = Registry.objects.filter(
                id__in=[reg.id for reg in user.registry.all()])

        return super(PatientAdmin, self).formfield_for_dbfield(dbfield, *args, **kwargs)

    def get_urls(self):
        search_url = url(
            r"search/(.*)$",
            self.admin_site.admin_view(
                self.search),
            name="patient_search")
        return [search_url] + super(PatientAdmin, self).get_urls()

    def get_queryset(self, request):
        self.request = request
        if request.user.is_superuser:
            return Patient.objects.all()
        user = get_user_model().objects.get(username=request.user)
        return Patient.objects.get_filtered(user)

    def search(self, request, term):
        # We have to do this against the result of self.queryset() to avoid
        # leaking patient details across working groups.
        queryset = self.queryset(request)

        try:
            # Check if the search term is numeric, in which case it's a record
            # ID.
            patient = queryset.get(id=int(term))
            response = [[patient.id, str(patient), str(patient.date_of_birth)]]
        except ValueError:
            # Guess not.
            patients = queryset.filter(Q(family_name__icontains=term) | Q(
                given_names__icontains=term)).order_by("family_name", "given_names")
            response = [[patient.id,
                         str(patient),
                         str(patient.date_of_birth)] for patient in patients]
        except Patient.DoesNotExist:
            response = []

        return HttpResponse(json.dumps(response), mimetype="application/json")

    def diagnosis_last_update(self, obj):
        return "%s" % obj.patient_diagnosis.updated

    diagnosis_last_update.allow_tags = True
    diagnosis_last_update.short_description = "Last Updated"

    def progress_graph(self, obj):
        if not hasattr(obj, 'patient_diagnosis'):
            return ''
        graph_html = '<a href="%s">' % reverse(
            'admin:{0}_diagnosis_change'.format(
                obj.patient_diagnosis._meta.app_label),
            args=(
                obj.id,
            ))
        graph_html += obj.patient_diagnosis.progress_graph()
        graph_html += '</a>'
        return graph_html

    progress_graph.allow_tags = True
    progress_graph.short_description = "Diagnosis Entry Progress"

    def moleculardata_entered(self, obj):
        if not hasattr(
                obj,
                'moleculardatasma') or not hasattr(
                obj.moleculardatasma,
                'variationsma_set') or not obj.moleculardatasma.variationsma_set.all():
            return ''

        imagefile = 'tick.png'

        genetic_url = '<a href="%s">' % reverse(
            'admin:genetic_moleculardatasma_change', args=(obj.id,))
        genetic_url += '<img src="%s"/>' % get_static_url("images/" + imagefile)
        genetic_url += '</a>'
        return genetic_url

    moleculardata_entered.allow_tags = True
    moleculardata_entered.short_description = "Genetic Data"

    def freshness(self, obj):
        """Used to show how recently the diagnosis was updated"""
        if not hasattr(obj, 'patient_diagnosis'):
            return ''

        delta = datetime.datetime.now() - obj.patient_diagnosis.updated
        age = delta.days

        if age > 365:
            imagefile = 'cross.png'
        else:
            imagefile = 'tick.png'

        return '<img src="%s"/>' % get_static_url("images/" + imagefile)

    freshness.allow_tags = True
    freshness.short_description = "Currency (updated in the last 365 days)"

    def last_updated(self, obj):
        if not hasattr(obj, 'diagnosis'):
            return ''
        delta = datetime.datetime.now() - obj.diagnosis.updated
        age = delta.days

        if age == 0:
            return 'today'
        if age == 1:
            return 'yesterday'
        else:
            return '%s days ago' % age

    last_updated.allow_tags = True
    last_updated.short_description = "Last updated"


class StateAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


class NextOfKinRelationshipAdmin(admin.ModelAdmin):
    model = NextOfKinRelationship


class AddressTypeAdmin(admin.ModelAdmin):
    model = AddressType
    list_display = ('type', 'description')


class ConsentValueAdmin(admin.ModelAdmin):
    model = ConsentValue
    list_display = (
        "patient", "registry", "consent_question", "answer", "first_save", "last_update")

    def registry(self, obj):
        return obj.consent_question.section.registry

    def queryset(self, request):
        qs = super(ConsentValueAdmin, self).queryset(request)
        if request.user.is_superuser:
            return qs
        else:
            return qs.filter(patient__rdrf_registry__in=request.user.registry.all())


class ParentGuardianAdmin(admin.ModelAdmin):
    model = ParentGuardian
    list_display = ('first_name', 'last_name', 'patients')

    def patients(self, obj):
        patients_string = ""
        patients = [p for p in obj.patient.all()]
        for patient in patients:
            patients_string += "%s %s<br>" % (patient.given_names, patient.family_name)
        return patients_string

    patients.allow_tags = True


class ClinicianOtherAdmin(admin.ModelAdmin):
    model = ClinicianOther
    list_display = ('clinician_last_name', 'clinician_first_name', 'clinician_hospital', 'clinician_address')


def unarchive_patient_action(modeladmin, request, archive_patients_selected):
    if request.user.is_superuser:
        for archived_patient in archive_patients_selected:
            archived_patient.active = True
            archived_patient.save()
            patient_id = archived_patient.id
            unarchive_clinicaldata_model(patient_id)


unarchive_patient_action.short_description = "Unarchive archived patient"


def hard_delete_patient_action(modeladmin, request, archive_patients_selected):
    if request.user.is_superuser:
        for archived_patient in archive_patients_selected:
            archived_patient._hard_delete()


hard_delete_patient_action.short_description = "Hard delete archived patient"


def unarchive_clinicaldata_model(patient_id):
    clinicaldata_models = ClinicalData.objects.filter(
        django_id=patient_id, django_model='Patient', collection='cdes')
    for cd in clinicaldata_models:
        cd.active = True
        cd.save()


class ArchivedPatientAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_name', 'date_of_birth', 'membership')
    actions = [unarchive_patient_action, hard_delete_patient_action]
    list_display_links = None

    def get_queryset(self, request):
        if not request.user.is_superuser:
            return []

        return Patient.objects.inactive()

    def has_add_permission(self, request, obj=None):
        return False

    def __init__(self, *args, **kwargs):
        super(ArchivedPatientAdmin, self).__init__(*args, **kwargs)

    def membership(self, patient_model):
        s = ""
        for r in patient_model.rdrf_registry.all().order_by('name'):
            s = s + r.name + "("
            for wg in patient_model.working_groups.filter(registry=r).order_by('name'):
                s = s + wg.name + " "
            s = s + ") "
        return s

# Use Proxy Model for Archived Patient as we can only register one model class once and the name
# comes from the model


def create_proxy_class(base_model, new_name):
    # Adapted from
    # http://stackoverflow.com/questions/2223375/multiple-modeladmins-views-for-same-model-in-django-admin
    class Meta:
        proxy = True
        app_label = base_model._meta.app_label
    attrs = {'__module__': '', 'Meta': Meta}
    proxy_class = type(new_name, (base_model,), attrs)
    return proxy_class


admin.site.register(Doctor, DoctorAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(NextOfKinRelationship, NextOfKinRelationshipAdmin)
admin.site.register(AddressType, AddressTypeAdmin)
admin.site.register(ParentGuardian, ParentGuardianAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(ConsentValue, ConsentValueAdmin)
admin.site.register(ClinicianOther, ClinicianOtherAdmin)
admin.site.register(create_proxy_class(Patient, "ArchivedPatient"), ArchivedPatientAdmin)

admin.site.disable_action('delete_selected')
