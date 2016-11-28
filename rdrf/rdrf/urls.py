from django.conf.urls import url, include
from django.contrib import admin
from django.shortcuts import render
from django.views.generic.base import TemplateView

import rdrf.form_view as form_view
import rdrf.registry_view as registry_view
import rdrf.landing_view as landing_view
import rdrf.import_registry_view as import_registry_view
import rdrf.patient_view as patient_view
import rdrf.login_router as login_router
import rdrf.report_view as report_view
import rdrf.consent_view as consent_view
from rdrf.registration_rdrf import RdrfRegistrationView
from rdrf.registry_list_view import RegistryListView
from rdrf.lookup_views import FamilyLookup
from rdrf.lookup_views import PatientLookup
from registry.patients.views import update_session
from registration.backends.default.views import ActivationView
from rdrf.family_linkage import FamilyLinkageView
from rdrf.email_notification_view import ResendEmail
from rdrf.permission_matrix import PermissionMatrixView
from rdrf.lookup_views import UsernameLookup
from rdrf.lookup_views import RecaptchaValidator
from rdrf.context_views import RDRFContextCreateView, RDRFContextEditView
from rdrf import patients_listing

# very important so that registry admins (genetic, patient, etc) are discovered.
admin.autodiscover()


def handler404(request):
    return render(request, "404.html")


def handler500(request):
    return render(request, "500.html")


def handlerApplicationError(request):
    return render(request, "rdrf_cdes/application_error.html", {
        "application_error": "Example config Error",
    })

import django.contrib.auth.views

urlpatterns = [
    url(r'^test404', handler404),
    url(r'^test500', handler500),
    url(r'^testAppError', handlerApplicationError),
    url(r'^iprestrict/', include('iprestrict.urls')),
    url(r'^useraudit/', include('useraudit.urls')),

    url(r'^api/v1/', include('rdrf.api_urls', namespace='v1')),
    url(r'^constructors/(?P<form_name>\w+)/?$',
        form_view.ConstructorFormView.as_view(), name="constructors"),
    url(r'^rpc', form_view.RPCHandler.as_view(), name='rpc'),

    url(r'^admin/', include(admin.site.urls)),
    url(r'', include('django.contrib.auth.urls')),
    url(r'', include('registry.urls', namespace="registry")),

    url(r'^$', landing_view.LandingView.as_view(), name='landing'),
    url(r'^reglist/?', RegistryListView.as_view(), name="reglist"),
    url(r'^import/?', import_registry_view.ImportRegistryView.as_view(),
        name='import_registry'),
    url(r'^reports/?', report_view.ReportView.as_view(), name="reports"),
    url(r'^reportdatatable/(?P<query_model_id>\d+)/?$', report_view.ReportDataTableView.as_view(),
        name="report_datatable"),
    url(r'^explorer/', include('explorer.urls')),
    url(r'^patientslisting/?', patients_listing.PatientsListingView.as_view(),
        name="patientslisting"),
    url(r'^contexts/(?P<registry_code>\w+)/(?P<patient_id>\d+)/add/(?P<context_form_group_id>\d+)?$',
        RDRFContextCreateView.as_view(),
        name="context_add"),
    url(r'contexts/(?P<registry_code>\w+)/(?P<patient_id>\d+)/(?P<context_id>\d+)/edit/?$',
        RDRFContextEditView.as_view(),
        name="context_edit"),
    url(r'^login/?$', django.contrib.auth.views.login,
        kwargs={'template_name': 'admin/login.html'}, name='login'),
    url(r'^router/', login_router.RouterView.as_view(), name="login_router"),

    url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<context_id>add)/?$",
        form_view.FormView.as_view(), name='form_add'),

    url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<context_id>\d+)?$",
        form_view.FormView.as_view(), name='registry_form'),

    url(r"^(?P<registry_code>\w+)/forms/print/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<context_id>\d+)?$",
        form_view.FormPrintView.as_view(), name='registry_form_print'),

    url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<section_code>\w+)/(?P<context_id>\d+)?/(?P<cde_code>\w+)/history/?$",
        form_view.FormFieldHistoryView.as_view(), name='registry_form_field_history'),

    url(r"^(?P<registry_code>\w+)/?$",
        registry_view.RegistryView.as_view(), name='registry'),

    url(r"^(?P<registry_code>\w+)/patient/add/?$",
        patient_view.AddPatientView.as_view(), name='patient_add'),

    url(r"^(?P<registry_code>\w+)/patient/(?P<patient_id>\d+)/edit$",
        patient_view.PatientEditView.as_view(), name='patient_edit'),

    url(r"^(?P<registry_code>\w+)/permissions/?$",
        PermissionMatrixView.as_view(), name='permission_matrix'),

    #---- Consent related URLs -----------------
    url(r"^(?P<registry_code>\w+)/consent/?$",
        consent_view.ConsentList.as_view(), name='consent_list'),

    url(r"^(?P<registry_code>\w+)/consent/(?P<section_id>\d+)/(?P<patient_id>\d+)/?$",
        consent_view.ConsentDetails.as_view(), name='consent_details'),

    url(r"^(?P<registry_code>\w+)/consent/print/?$",
        consent_view.PrintConsentList.as_view(), name='print_consent_list'),

    url(r"^(?P<registry_code>\w+)/(?P<patient_id>\d+)/consents/?$",
        form_view.CustomConsentFormView.as_view(), name="consent_form_view"),

    url(r"^(?P<registry_code>\w+)/(?P<patient_id>\d+)/consents/print/?$",
        consent_view.ConsentDetailsPrint.as_view(), name="print_consent_details"),

    #-------------------------------------------

    #---- Email Notifications URLs -------------
    url(r"^resend_email/(?P<notification_history_id>\w+)/?$",
        ResendEmail.as_view(), name="resend_email"),
    #-------------------------------------------

    url(r"^(?P<registry_code>\w+)/familylinkage/(?P<initial_index>\d+)?$",
        FamilyLinkageView.as_view(), name='family_linkage'),

    url(r'^(?P<registry_code>\w+)/questionnaire/(?P<questionnaire_context>\w+)?$',
        form_view.QuestionnaireView.as_view(), name='questionnaire'),
    url(r'^(?P<registry_code>\w+)/approval/(?P<questionnaire_response_id>\d+)/?$', form_view.QuestionnaireHandlingView.as_view(),
        name='questionnaire_response'),
    url(r'^(?P<registry_code>\w+)/uploads/(?P<file_id>([0-9a-fA-F]{24})|(\d+))$',
        form_view.FileUploadView.as_view(), name='file_upload'),

    url(r'^admin/lookups/', include('ajax_select.urls')),

    url(r'^admin/patients/updatesession/?$',
        update_session, name='updatesession'),
    url(r'^questionnaireconfig/(?P<form_pk>\d+)/?$',
        form_view.QuestionnaireConfigurationView.as_view(), name='questionnaire_config'),
    url(r'^designer/(?P<reg_pk>\d+)$',
        form_view.RDRFDesigner.as_view(), name='rdrf_designer'),
    url(r'^cdes', form_view.RDRFDesignerCDESEndPoint.as_view(),
        name='rdrf_designer_cdes_endpoint'),
    url(r'^registrystructure/(?P<reg_pk>\d+)$', form_view.RDRFDesignerRegistryStructureEndPoint.as_view(),
        name='rdrf_designer_registry_structure_endpoint'),
    url(r'^adjudicationinitiation/(?P<def_id>\d+)/(?P<patient_id>\d+)/?$',
        form_view.AdjudicationInitiationView.as_view(), name='adjudication_initiation'),
    url(r'^adjudicationrequest/(?P<adjudication_request_id>\d+)/?$',
        form_view.AdjudicationRequestView.as_view(), name='adjudication_request'),
    url(r'^adjudicationresult/(?P<adjudication_definition_id>\d+)/(?P<requesting_user_id>\d+)/(?P<patient_id>\d+)/?$',
        form_view.AdjudicationResultsView.as_view(), name='adjudication_result'),



    url(r'api/familylookup/(?P<reg_code>\w+)/?$', FamilyLookup.as_view(), name="family_lookup"),
    url(r'api/patientlookup/(?P<reg_code>\w+)/?$', PatientLookup.as_view(), name="patient_lookup"),

    #---- Look-ups URLs -----------------------
    url(r"^lookup/username/(?P<username>[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})/?$",
        UsernameLookup.as_view(), name="lookup_username"),

    url(r"^lookup/recaptcha/?$",
        RecaptchaValidator.as_view(), name="recaptcha_validator"),
    #-------------------------------------------

    url(r'^(?P<registry_code>\w+)/register/$',
        RdrfRegistrationView.as_view(),
        name='registration_register'),
    url(r'^register/complete/$',
        TemplateView.as_view(
            template_name='registration/registration_complete.html'),
        name='registration_complete'),
    url(r'^register/closed/$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'),
        name='registration_disallowed'),
    url(r'^activate/complete/$',
        TemplateView.as_view(
            template_name='registration/activation_complete.html'),
        name='registration_activation_complete'),

    url(r'^activate/(?P<activation_key>\w+)/$',
        ActivationView.as_view(),
        name='registration_activate'),

    url(r'^i18n/', include('django.conf.urls.i18n')),
]
