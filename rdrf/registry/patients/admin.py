from django.conf.urls import patterns, url
from django.contrib import admin
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.core import urlresolvers
from django.conf import settings
from admin_views.admin import AdminViews
import os
import json, datetime

from registry.utils import get_static_url, get_working_groups
from admin_forms import *
from models import *


class CountryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


class DoctorAdmin(admin.ModelAdmin):
    search_fields = ["family_name", "given_names"]


class PatientDoctorAdmin(admin.TabularInline):
    fields = ["relationship", "doctor"]
    form = PatientDoctorForm
    model = PatientDoctor

class ParentAdmin(admin.ModelAdmin):
    model = Parent

class PatientParentAdmin(admin.TabularInline):
    fields = ["relationship", "parent"]
    form = PatientParentForm
    model = PatientParent
    extra = 1

class PatientConsentAdmin(admin.TabularInline):
    model = PatientConsent
    extra = 1

class PatientAdmin(AdminViews, admin.ModelAdmin):
    app_url = os.environ.get("SCRIPT_NAME", "")
    form = PatientForm
    admin_views = (
        ('Patient Report (SuperUser only)', '%s/%s' % (app_url, 'reports/patient/')),
    )

    inlines = [PatientConsentAdmin, PatientParentAdmin, PatientDoctorAdmin]
    search_fields = ["family_name", "given_names"]
    list_display = ['__unicode__', 'progress_graph', 'moleculardata_entered', 'freshness', 'working_group', 'diagnosis_last_update']

    def create_fieldset(self, superuser=False):
        """Function to dynamically create the fieldset, adding 'active' field if user is a superuser"""

        consent = ("Consent", {
            "fields":(
                "consent",
             )
        })

        personal_details = ("Personal Details", {})

        personal_details_fields = ["working_group",
                                   "family_name",
                                   "given_names",
                                   "umrn",
                                   "date_of_birth",
                                   "place_of_birth",
                                   "date_of_migration",
                                   "sex",
                                   "address",
                                   "suburb",
                                   "state",
                                   "postcode",
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

        fieldset = (consent, personal_details, next_of_kin,)
        return fieldset

    def get_fieldsets(self, request, obj=None):
        return self.create_fieldset(request.user.is_superuser)

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []
        else:
            #return ['active'] # NB this seems to run into a mango bug that prevents Add Patient being used by non-superuser
            return []

    def formfield_for_dbfield(self, dbfield, *args, **kwargs):
        from registry.groups.models import User, WorkingGroup

        request = kwargs.get('request')
        user = request.user
        # Restrict normal users to their own working group.
        if dbfield.name == "working_group" and not user.is_superuser:
            user = User.objects.get(user=user) # get the user's associated objects
            #kwargs["queryset"] = WorkingGroup.objects.filter(id__in = get_working_groups(user))
            kwargs["queryset"] = WorkingGroup.objects

        return super(PatientAdmin, self).formfield_for_dbfield(dbfield, *args, **kwargs)

    def get_urls(self):
        urls = super(PatientAdmin, self).get_urls()
        local_urls = patterns("",
            url(r"search/(.*)$", self.admin_site.admin_view(self.search), name="patient_search")
        )
        return local_urls + urls

    def queryset(self, request):
        import registry.groups.models

        if request.user.is_superuser:
            return Patient.objects.all()

        user = registry.groups.models.User.objects.get(user=request.user)
        return Patient.objects.filter(working_group__in=get_working_groups(user)).filter(active=True)

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
    list_display = ["name", "country"]
    search_fields = ["name"]

class NextOfKinRelationshipAdmin(admin.ModelAdmin):
    model = NextOfKinRelationship

admin.site.register(Country, CountryAdmin)
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(Patient, PatientAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(NextOfKinRelationship, NextOfKinRelationshipAdmin)
admin.site.register(Parent, ParentAdmin)
admin.site.disable_action('delete_selected')
