from django.conf.urls import patterns, url
from django.contrib import admin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.core import urlresolvers
from django.core.urlresolvers import reverse
from django.conf import settings
import os
import json
import datetime
from rdrf.utils import de_camelcase
from rdrf.models import Registry, RegistryForm
from registry.utils import get_static_url, get_working_groups, get_registries
from admin_forms import *
from models import *
from rdrf.dynamic_data import DynamicDataWrapper
from django.contrib.auth import get_user_model
import logging
from rdrf.utils import has_feature

logger = logging.getLogger("registry_log")


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
        self.list_display_links = (None, )

    app_url = os.environ.get("SCRIPT_NAME", "")
    form = PatientForm
    request = None

    inlines = [PatientAddressAdmin, PatientConsentAdmin, PatientDoctorAdmin, PatientRelativeAdmin]
    search_fields = ["family_name", "given_names"]
    if has_feature('adjudication'):
        list_display = ['full_name', 'working_groups_display', 'get_reg_list', 'date_of_birth', 'demographic_btn', 'data_modules_btn', 'adjudications_btn']
    else:
        list_display = ['full_name', 'working_groups_display', 'get_reg_list', 'date_of_birth', 'demographic_btn', 'data_modules_btn']

    list_filter = [RegistryFilter]
    
    def full_name(self, obj):
        return obj.__unicode__()

    full_name.short_description = 'Name'

    def demographic_btn(self, obj):
        return "<a href='%s' class='btn btn-info btn-small'>Details</a>" % reverse('admin:patients_patient_change', args=(obj.id,))
    
    demographic_btn.allow_tags = True
    demographic_btn.short_description = 'Demographics'

    def data_modules_btn(self, obj):
        if obj.rdrf_registry.count() == 0:
            return "No registry assigned"
        
        rdrf_id = self.request.GET.get('registry')
        
        if not rdrf_id and Registry.objects.count() > 1:
            return "Please filter registry"

        def nice_name(name):
            try:
                return de_camelcase(name)
            except:
                return name
        
        rdrf = Registry.objects.get(pk=rdrf_id)
        not_generated = lambda frm: not frm.name.startswith(rdrf.generated_questionnaire_name)
        forms = [f for f in RegistryForm.objects.filter(registry=rdrf).order_by('position') if not_generated(f)]

        content = ''
        
        if not forms:
            content = "No modules available"

        if len(forms) == 1:
            url = reverse('registry_form', args=(rdrf.code, forms[0].id, obj.id))
            return "<a href='%s' class='btn btn-info btn-small'>Details</a>" % url

        for form in forms:
            url = reverse('registry_form', args=(rdrf.code, form.id, obj.id))
            content += "<a href=%s>%s</a><br/>" % (url, nice_name(form.name))
        
        return "<button type='button' class='btn btn-info btn-small' data-toggle='popover' data-content='%s' id='data-modules-btn'>Show Modules</button>" % content
    
    data_modules_btn.allow_tags = True
    data_modules_btn.short_description = 'Data Modules'

    def adjudications_btn(self, obj):
        content = ""
        if obj.rdrf_registry.count() == 0:
            return "No registry assigned"

        rdrf_id = self.request.GET.get('registry')

        if not rdrf_id and Registry.objects.count() > 1:
            return "Please filter registry"
        registry = Registry.objects.get(pk=rdrf_id)
        adjudication_actions = registry.get_adjudications()
        if not adjudication_actions:
            content = "No actions available"

        if len(adjudication_actions) == 1:
            action = adjudication_actions[0]
            args = action.args + [obj.id]
            url = reverse(action.url_name, args=args)
            return "<a href='%s' class='btn btn-info btn-small'>%s</a>" % (url, action.display_name)

        for adjudication_action in adjudication_actions:
            args = adjudication_actions.args + [obj.id]
            url = reverse(adjudication_action.url_name, args=args)
            content += "<a href=%s>%s</a><br/>" % (url, adjudication_action.display_name)

        return "<button type='button' class='btn btn-info btn-small' data-toggle='popover' data-content='%s' id='patient-actions-btn'>Available Actions</button>" % content

    adjudications_btn.allow_tags = True
    adjudications_btn.short_description = 'Available Adjudications'

    def get_form(self, request, obj=None, **kwargs):
        # NB. This method returns a form class
        user = get_user_model().objects.get(username=request.user)
        registry_specific_fields = self._get_registry_specific_patient_fields(user)
        self.form = self._add_registry_specific_fields(self.form, registry_specific_fields)
        form = super(PatientAdmin, self).get_form(request, obj, **kwargs)
        form.user = user
        form.is_superuser = request.user.is_superuser
        return form

    def render_change_form(self, *args, **kwargs):
        #return self.render_change_form(request, context, change=True, obj=obj, form_url=form_url)
        context = args[1]
        if 'original' in context:
            patient = context['original']
            context['form_links'] = self._get_formlinks(patient)
        return super(PatientAdmin, self).render_change_form(*args, **kwargs)

    def _get_formlinks(self, patient):
        from rdrf.utils import FormLink
        links = []
        for registry_model in patient.rdrf_registry.all():
            for form_model in registry_model.forms:
                if form_model.is_questionnaire:
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
            field_dict = {"fields": [pair[0].code for pair in cde_field_pairs]}  # pair up cde name and field object generated from that cde
            fieldsets.append((fieldset_title, field_dict))
        return fieldsets

    def create_fieldset(self, user):

        consent = ("Consent", {
            "fields": (
                "consent",
                "consent_clinical_trials",
                "consent_sent_information",
            )
        })
        
        rdrf_registry = ("Registry", {
            "fields": (
                "rdrf_registry",
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

        # fix for Trac #3, the field is now always displayed, but readonly for not superuser users, see get_readonly_fields below
        personal_details_fields.append("active")
        personal_details_fields.append("inactive_reason")

        personal_details[1]["fields"] = tuple(personal_details_fields)

        next_of_kin = ("Next of Kin", {
            "fields":
            ("next_of_kin_family_name",
             "next_of_kin_given_names",
             "next_of_kin_relationship",
             "next_of_kin_address",
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
        fieldset.extend(self._get_registry_specific_fieldsets(user))
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
        registry_specific_fields_dict = self._get_registry_specific_patient_fields(request.user)

        for reg_code in registry_specific_fields_dict:
            mongo_patient_data[reg_code] = {}
            registry_specific_fields = registry_specific_fields_dict[reg_code]
            for cde, field_object in registry_specific_fields:
                field_name = cde.name
                cde_code = cde.code
                field_value = request.POST[cde.code]
                mongo_patient_data[reg_code][cde_code] = field_value

                logger.debug("specific field for %s %s = %s" % (reg_code, field_name, field_value))

        if mongo_patient_data:
            instance.mongo_patient_data = mongo_patient_data

        return instance

    def save_model(self, request, obj, form, change):
        """
        Override ModelAdmin code to allow us to save the registry specific patient to Mongo ...
        """
        obj.save()

        if hasattr(obj, 'mongo_patient_data'):
            patient_id = obj.pk
            self._save_registry_specific_data_in_mongo(obj)

    def save_formset(self, request, form, formset, change):
        """
        Given an inline formset save it to the database.
        """
        if formset.__class__.__name__ == 'PatientRelativeFormFormSet':
            # check to see if we're creating a patient from this relative
            logger.debug("saving patient relative")
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
            #return ['active'] # NB this seems to run into a mango bug that prevents Add Patient being used by non-superuser
            return []

    def formfield_for_dbfield(self, dbfield, *args, **kwargs):
        from registry.groups.models import WorkingGroup

        request = kwargs.get('request')
        user = request.user
        # Restrict normal users to their own working group.
        if dbfield.name == "working_groups" and not user.is_superuser:
            user = get_user_model().objects.get(username=user)  # get the user's associated objects
            kwargs["queryset"] = WorkingGroup.objects.filter(id__in=get_working_groups(user))

        if dbfield.name == "rdrf_registry" and not user.is_superuser:
            user = get_user_model().objects.get(username=user)
            kwargs["queryset"] = Registry.objects.filter(id__in=[reg.id for reg in user.registry.all()])   

        return super(PatientAdmin, self).formfield_for_dbfield(dbfield, *args, **kwargs)

    def get_urls(self):
        urls = super(PatientAdmin, self).get_urls()
        local_urls = patterns("", url(r"search/(.*)$", self.admin_site.admin_view(self.search), name="patient_search"))
        return local_urls + urls

    def queryset(self, request):
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
            response = [[patient.id, unicode(patient), unicode(patient.date_of_birth)]]
        except ValueError:
            # Guess not.
            patients = queryset.filter(Q(family_name__icontains=term) | Q(given_names__icontains=term)).order_by("family_name", "given_names")
            response = [[patient.id, unicode(patient), unicode(patient.date_of_birth)] for patient in patients]
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
        graph_html = '<a href="%s">' % urlresolvers.reverse('admin:{0}_diagnosis_change'.format(obj.patient_diagnosis._meta.app_label), args=(obj.id,))
        graph_html += obj.patient_diagnosis.progress_graph()
        graph_html += '</a>'
        return graph_html

    progress_graph.allow_tags = True
    progress_graph.short_description = "Diagnosis Entry Progress"

    def moleculardata_entered(self, obj):
        if not hasattr(obj, 'moleculardatasma') or not hasattr(obj.moleculardatasma, 'variationsma_set') or not obj.moleculardatasma.variationsma_set.all():
            return ''

        imagefile = 'tick.png'

        genetic_url = '<a href="%s">' % urlresolvers.reverse('admin:genetic_moleculardatasma_change', args=(obj.id,))
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


admin.site.register(Doctor, DoctorAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(NextOfKinRelationship, NextOfKinRelationshipAdmin)
admin.site.register(AddressType, AddressTypeAdmin)

admin.site.disable_action('delete_selected')
