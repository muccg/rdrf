from __future__ import absolute_import
from django.conf.urls import patterns, url, include
from django.conf import settings
from django.contrib import admin
from django.shortcuts import render_to_response
from django.views.generic.base import TemplateView

import registry.urls as common_urls
import rdrf.form_view as form_view
import rdrf.registry_view as registry_view
import rdrf.landing_view as landing_view
import rdrf.import_registry_view as import_registry_view
import rdrf.rest_interface as rest_interface
import rdrf.hgvs_view as hgvs_view
import rdrf.patient_view as patient_view
import rdrf.parent_view as parent_view
import rdrf.login_router as login_router
import rdrf.report_view as report_view
import rdrf.consent_view as consent_view
from rdrf.registration_rdrf import RdrfRegistrationView
from rdrf.registry_list_view import RegistryListView
from rdrf.lookup_views import GeneView, LaboratoryView, StateLookup, ClinitianLookup, IndexLookup, FamilyLookup
from rdrf.views import RegistryList
from rdrf.api import PatientResource
from registry.patients.views import update_session
from registration.backends.default.views import ActivationView
from rdrf.family_linkage import FamilyLinkageView
from rdrf.email_notification_view import ResendEmail
from rdrf.permission_matrix import PermissionMatrixView
from rdrf.lookup_views import UsernameLookup
from rdrf.lookup_views import RDRFContextLookup
from rdrf.lookup_views import RecaptchaValidator
from rdrf.context_views import RDRFContextCreateView, RDRFContextEditView



from ajax_select import urls as ajax_select_urls
from tastypie.api import Api


# very important so that registry admins (genetic, patient, etc) are discovered.
admin.autodiscover()


def handler404(request):
    return render_to_response("error/404.html")


def handler500(request):
    return render_to_response("error/500.html")


def handlerApplicationError(request):
    return render_to_response(
        "rdrf_cdes/application_error.html", {"application_error": "Example config Error"})


# TastyPie API
v1_api = Api(api_name='v1')
v1_api.register(PatientResource())

urlpatterns = patterns('',
                       url(r'^test404', handler404),
                       url(r'^test500', handler500),
                       url(r'^testAppError', handlerApplicationError),
                       url(r'^constructors/(?P<form_name>\w+)/?$',
                           form_view.ConstructorFormView.as_view(), name="constructors"),
                       url(r'^rpc', form_view.RPCHandler.as_view(), name='rpc'),

                       (r'^admin/', include(admin.site.urls)),
                       (r'', include('django.contrib.auth.urls')),
                       (r'', include(common_urls, namespace="registry")),

                       url(r'^/?$', landing_view.LandingView.as_view(), name='landing'),
                       url(r'^reglist/?', RegistryListView.as_view(), name="reglist"),
                       url(r'^import/?', import_registry_view.ImportRegistryView.as_view(),
                           name='import_registry'),
                       url(r'^reports/?', report_view.ReportView.as_view(), name="reports"),
                       url(r'^explorer/', include('explorer.urls')),
                       url(r'^gene/?$', GeneView.as_view(), name='gene_source'),
                       url(r'^laboratory/?$', LaboratoryView.as_view(),
                           name='laboratory_source'),

                       url(r'^hgvs/?$', hgvs_view.HGVSView.as_view(), name='hgvs_validator'),
                       url(r'^listregistry/?$', RegistryList.as_view(), name='registry_list'),

                       # url(r'^patientslisting/?', form_view.PatientsListingView.as_view(),
                       #     name="patientslisting"),
                       url(r'^patientsgridapi/?$', form_view.DataTableServerSideApi.as_view(),
                           name='patientsgridapi'),
                       #---- Context related URLs -----------------
                       url(r'^contextslisting/?', form_view.ContextsListingView.as_view(),
                           name="contextslisting"),

                       url(r'^contextsgridapi/?$', form_view.ContextDataTableServerSideApi.as_view(),
                           name='contextsgridapi'),

                       url(r'^contexts/(?P<registry_code>\w+)/(?P<patient_id>\d+)/add/?$',
                           RDRFContextCreateView.as_view(),
                           name="context_add"),
                       url(r'contexts/(?P<registry_code>\w+)/(?P<patient_id>\d+)/(?P<context_id>\d+)/edit/?$',
                           RDRFContextEditView.as_view(),
                           name="context_edit"),
                       url(r'^bootgridapi', form_view.BootGridApi.as_view()),

                       url(r'^login/?$', 'django.contrib.auth.views.login',
                           {'template_name': 'admin/login.html'}, name='login'),
                       url(r'^router/', login_router.RouterView.as_view(), name="login_router"),

                       url(r"^(?P<registry_code>\w+)/forms/(?P<form_id>\w+)/(?P<patient_id>\d+)/(?P<context_id>\d+)?$",
                           form_view.FormView.as_view(), name='registry_form'),

                       url(r"^(?P<registry_code>\w+)/forms/print/(?P<form_id>\w+)/(?P<patient_id>\d+)$",
                           form_view.FormPrintView.as_view(), name='registry_form_print'),
                       
                       url(r"^(?P<registry_code>\w+)/?$",
                           registry_view.RegistryView.as_view(), name='registry'),

                       url(r"^(?P<registry_code>\w+)/patient/(?P<context_id>\d+)?$",
                           patient_view.PatientView.as_view(), name='patient_page'),
                       url(r"^(?P<registry_code>\w+)/patient/add/?$",
                           patient_view.AddPatientView.as_view(), name='patient_add'),

                       url(r"^(?P<registry_code>\w+)/patient/(?P<patient_id>\d+)/(?P<context_id>\d+)?$",
                           patient_view.PatientEditView.as_view(), name='patient_edit'),

                       url(r"^(?P<registry_code>\w+)/patient/to-parent/(?P<patient_id>\d+)/?$",
                           patient_view.PatientToParentView.as_view(), name='patient_to_parent'),

                       url(r"^(?P<registry_code>\w+)/permissions/?$",
                           PermissionMatrixView.as_view(), name='permission_matrix'),

#---- Consent related URLs -----------------
                       url(r"^(?P<registry_code>\w+)/consent/?$",
                           consent_view.ConsentList.as_view(), name='consent_list'),

                       url(r"^(?P<registry_code>\w+)/consent/(?P<section_id>\d+)/(?P<patient_id>\d+)/?$",
                           consent_view.ConsentDetails.as_view(), name='consent_details'),

                       url(r"^(?P<registry_code>\w+)/consent/print/?$",
                           consent_view.PrintConsentList.as_view(), name='print_consent_list'),

                       url(r"^(?P<registry_code>\w+)/(?P<patient_id>\d+)/consents/(?P<context_id>\d+)?$",
                           form_view.CustomConsentFormView.as_view(), name="consent_form_view"),
#-------------------------------------------

#---- Email Notifications URLs -------------
                       url(r"^resend_email/(?P<notification_history_id>\w+)/?$",
                           ResendEmail.as_view(), name="resend_email"),
#-------------------------------------------

#---- Parent URLs --------------------------
                       url(r"^(?P<registry_code>\w+)/parent/(?P<context_id>\d+)?$",
                           parent_view.ParentView.as_view(), name='parent_page'),

                       url(r"^(?P<registry_code>\w+)/parent/(?P<parent_id>\d+)/(?P<context_id>\d+)?$",
                           parent_view.ParentEditView.as_view(), name='parent_edit'),
#-------------------------------------------

                       url(r"^(?P<registry_code>\w+)/familylinkage/(?P<initial_index>\d+)?$",
                           FamilyLinkageView.as_view(), name='family_linkage'),

                       url(r'^(?P<registry_code>\w+)/questionnaire/(?P<questionnaire_context>\w+)?$',
                           form_view.QuestionnaireView.as_view(), name='questionnaire'),
                       url(r'^(?P<registry_code>\w+)/approval/(?P<questionnaire_response_id>\d+)/?$', form_view.QuestionnaireResponseView.as_view(),
                           name='questionnaire_response'),
                       url(r'^(?P<registry_code>\w+)/uploads/(?P<gridfs_file_id>\w+)$',
                           form_view.FileUploadView.as_view(), name='file_upload'),
                       url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/(?P<form_name>.+?)/(?P<section_code>.+?)/(?P<cde_code>.+?)/?$',
                           rest_interface.RDRFEndpointView.as_view(), name='rest_cde_interface'),
                       url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/(?P<form_name>.+?)/(?P<section_code>.+?)/?$',
                           rest_interface.RDRFEndpointView.as_view(), name='rest_section_interface'),
                       url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/(?P<form_name>.+?)/?$',
                           rest_interface.RDRFEndpointView.as_view(), name='rest_form_interface'),
                       url(r'^(?P<registry_code>\w+)/patients/(?P<patient_id>\d+)?/?$',
                           rest_interface.RDRFEndpointView.as_view(), name='rest_interface'),
                       (r'^admin/lookups/', include(ajax_select_urls)),

                       url(r'^admin/patients/updatesession/?$',
                           update_session, name='updatesession'),
                       (r'^api/', include(v1_api.urls)),
                       url(r'^state/(?P<country_code>\w+)/?$',
                           StateLookup.as_view(), name='state_lookup'),
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

                       url(r'^api/clinitian/',
                           ClinitianLookup.as_view(), name="clinician_lookup"),

                       url(r'api/indexlookup/(?P<reg_code>\w+)/?$', IndexLookup.as_view(), name="index_lookup"),

                       url(r'api/familylookup/(?P<reg_code>\w+)/?$', FamilyLookup.as_view(), name="family_lookup"),

#---- Look-ups URLs -----------------------
                       url(r"^lookup/username/(?P<username>[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})/?$",
                           UsernameLookup.as_view(), name="lookup_username"),
                       
                       url(r"^lookup/recaptcha/?$",
                           RecaptchaValidator.as_view(), name="recaptcha_validator"),
#-------------------------------------------

                       url(r'api/contextlookup/(?P<registry_code>\w+)/(?P<patient_id>\d+)/?$',
                           RDRFContextLookup.as_view(),
                           name="rdrf_context_lookup"))


urlpatterns += patterns('',
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
                        url(r'^iprestrict/',
                            include('iprestrict.urls')),
                        )

urlpatterns += patterns('',
                        url(r'^i18n', include('django.conf.urls.i18n')),
                        )

# pattern for serving statically
if settings.DEBUG:
    urlpatterns += patterns('',
                            (r'^static/(?P<path>.*)$', 'django.views.static.serve',
                             {'document_root': settings.STATIC_ROOT, 'show_indexes': True}))
