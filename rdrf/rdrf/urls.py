from django.conf.urls import url, include
from django.contrib import admin
from django.shortcuts import render
from django.views.generic.base import TemplateView
from django.contrib.auth import views as auth_views
from django.views.i18n import JavaScriptCatalog
from django.conf import settings
from django.utils.translation import ugettext as _

from two_factor import views as twv

from rdrf.auth.forms import RDRFLoginAssistanceForm, RDRFPasswordResetForm, RDRFSetPasswordForm
from rdrf.auth.views import login_assistance_confirm, QRGeneratorView, SetupView

import rdrf.views.form_view as form_view
import rdrf.views.registry_view as registry_view
import rdrf.views.landing_view as landing_view
import rdrf.views.import_registry_view as import_registry_view
import rdrf.views.patient_view as patient_view
import rdrf.routing.login_router as login_router
import rdrf.views.report_view as report_view
import rdrf.views.consent_view as consent_view
from rdrf.views.registration_rdrf import RdrfRegistrationView
from rdrf.views.registry_list_view import RegistryListView
from rdrf.views.lookup_views import FamilyLookup
from rdrf.views.lookup_views import PatientLookup
from registration.backends.default.views import ActivationView
from rdrf.views.family_linkage import FamilyLinkageView
from rdrf.views.email_notification_view import ResendEmail
from rdrf.views.permission_matrix import PermissionMatrixView
from rdrf.views.lookup_views import UsernameLookup
from rdrf.views.lookup_views import RecaptchaValidator
from rdrf.views.context_views import RDRFContextCreateView, RDRFContextEditView
from rdrf.views import patients_listing
from rdrf.views import clinician_view
from rdrf.views.verification_views import PatientsRequiringVerificationView
from rdrf.views.verification_views import PatientVerificationView


import logging


logger = logging.getLogger(__name__)

# very important so that registry admins (genetic, patient, etc) are discovered.
admin.autodiscover()


def handler_exceptions(request):
    raise Exception("Forced exception in /raise")


def handler404(request):
    return render(request, "404.html")


def handler500(request):
    return render(request, "500.html")


def handler_application_error(request):
    return render(request, "rdrf_cdes/application_error.html", {
        "application_error": "Example config Error",
    })


JavaScriptCatalog.domain = "django"  # The default domain didn't work for me

urlpatterns = []
if settings.DEBUG is True:
    urlpatterns += [
        url(r'^test404', handler404, name='test 404'),
        url(r'^test500', handler500, name='test 500'),
        url(r'^testAppError', handler_application_error, name='test application error'),
        url(r'^raise', handler_exceptions, name='test exception'),
    ]


two_factor_auth_urls = [
    url(
        regex=r'^account/login/?$',
        view=twv.LoginView.as_view(),
        name='login',
    ),
    url(
        regex=r'^account/two_factor/setup/?$',
        view=SetupView.as_view(),
        name='setup',
    ),
    url(
        regex=r'^account/two_factor/qrcode/?$',
        view=QRGeneratorView.as_view(),
        name='qr',
    ),
    url(
        regex=r'^account/two_factor/setup/complete/?$',
        view=twv.SetupCompleteView.as_view(),
        name='setup_complete',
    ),
    #    We're not using a few of these urls currently
    #
    #    url(
    #        regex=r'^account/two_factor/backup/tokens/?$',
    #        view=twv.BackupTokensView.as_view(),
    #        name='backup_tokens',
    #    ),
    #    url(
    #        regex=r'^account/two_factor/backup/phone/register/?$',
    #        view=twv.PhoneSetupView.as_view(),
    #        name='phone_create',
    #    ),
    #    url(
    #        regex=r'^account/two_factor/backup/phone/unregister/(?P<pk>\d+)/?$',
    #        view=twv.PhoneDeleteView.as_view(),
    #        name='phone_delete',
    #    ),
    #    url(
    #        regex=r'^account/two_factor/?$',
    #        view=twv.ProfileView.as_view(),
    #        name='profile',
    #    ),
    url(
        regex=r'^account/two_factor/disable/?$',
        view=twv.DisableView.as_view(),
        name='disable',
    ),
]


urlpatterns += [
    url(r'^translations/jsi18n/$', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    url(r'^iprestrict/', include('iprestrict.urls')),
    url(r'^useraudit/', include('useraudit.urls')),

    url(r'^api/v1/', include('rdrf.services.rest.urls.api_urls', namespace='v1')),
    url(r'^constructors/(?P<form_name>\w+)/?$',
        form_view.ConstructorFormView.as_view(), name="constructors"),
    url(r'^rpc', form_view.RPCHandler.as_view(), name='rpc'),

    url(r'^admin/', include(admin.site.urls)),

    url(r'', include(two_factor_auth_urls, 'two_factor')),

    # django.contrib.auth URLs listed expicitly so we can override some of them for custom behaviour
    # Kept the original urls commented out to have an easy view on which URLs are customised.
    # Login is done by two_factor:login included above

    url(r'^logout/?$', auth_views.logout, name='logout'),
    url(r'^password_change/?$', auth_views.password_change, name='password_change'),
    url(r'^password_change/done/?$', auth_views.password_change_done, name='password_change_done'),
    # url(r'^password_reset/$', views.password_reset, name='password_reset'),
    url(r'^password_reset/?$', auth_views.password_reset,
        kwargs={'password_reset_form': RDRFPasswordResetForm}, name='password_reset'),
    url(r'^password_reset/done/?$', auth_views.password_reset_done, name='password_reset_done'),
    # url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
    #     auth_views.password_reset_confirm, name='password_reset_confirm'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/?$',
        auth_views.password_reset_confirm,
        kwargs={'set_password_form': RDRFSetPasswordForm},
        name='password_reset_confirm'),
    url(r'^reset/done/?$', auth_views.password_reset_complete, name='password_reset_complete'),

    # Login trouble self assistance URLs
    url(r'^login_assistance/?$', auth_views.password_reset,
        kwargs={
            'password_reset_form': RDRFLoginAssistanceForm,
            'template_name': 'registration/login_assistance_form.html',
            'subject_template_name': 'registration/login_assistance_subject.txt',
            'email_template_name': 'registration/login_assistance_email.html',
            'post_reset_redirect': 'login_assistance_email_sent',
        },
        name='login_assistance'),
    url(r'^login_assistance/sent/?$', auth_views.password_reset_done,
        kwargs={'template_name': 'registration/login_assistance_sent.html',
                'extra_context': {'title': _('Login Assitance Email Sent')}},
        name='login_assistance_email_sent'),
    url(r'^login_assistance_confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/?$',
        login_assistance_confirm,
        name='login_assistance_confirm'),
    url(r'^login_assistance/complete/?$', auth_views.password_reset_complete,
        kwargs={'template_name': 'registration/login_assistance_complete.html'},
        name='login_assistance_complete'),


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

    # ---- Consent related URLs -----------------
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

    # -------------------------------------------
    # ---- Clinician related URLs -----------------
    url(r"^(?P<registry_code>\w+)/(?P<patient_id>\d+)/clinician/?$",
        clinician_view.ClinicianFormView.as_view(), name="clinician_form_view"),

    url(r"^(?P<registry_code>\w+)/verifications/?$",
        PatientsRequiringVerificationView.as_view(), name='verifications_list'),

    url(r"^(?P<registry_code>\w+)/verifications/(?P<patient_id>\d+)?$",
        PatientVerificationView.as_view(), name='patient_verification'),

    # ---- Email Notifications URLs -------------
    url(r"^resend_email/(?P<notification_history_id>\w+)/?$",
        ResendEmail.as_view(), name="resend_email"),
    # -------------------------------------------
    url(r"^(?P<registry_code>\w+)/familylinkage/(?P<initial_index>\d+)?$",
        FamilyLinkageView.as_view(), name='family_linkage'),

    url(r'^(?P<registry_code>\w+)/questionnaire/(?P<questionnaire_context>\w+)?$',
        form_view.QuestionnaireView.as_view(), name='questionnaire'),
    url(r'^(?P<registry_code>\w+)/approval/(?P<questionnaire_response_id>\d+)/?$', form_view.QuestionnaireHandlingView.as_view(),
        name='questionnaire_response'),
    url(r'^(?P<registry_code>\w+)/uploads/(?P<file_id>([0-9a-fA-F]{24})|(\d+))$',
        form_view.FileUploadView.as_view(), name='file_upload'),
    url(r'^admin/lookups/', include('ajax_select.urls')),
    url(r'^questionnaireconfig/(?P<form_pk>\d+)/?$',
        form_view.QuestionnaireConfigurationView.as_view(), name='questionnaire_config'),
    url(r'^designer/(?P<reg_pk>\d+)$',
        form_view.RDRFDesigner.as_view(), name='rdrf_designer'),
    url(r'^cdes', form_view.RDRFDesignerCDESEndPoint.as_view(),
        name='rdrf_designer_cdes_endpoint'),
    url(r'^registrystructure/(?P<reg_pk>\d+)$', form_view.RDRFDesignerRegistryStructureEndPoint.as_view(),
        name='rdrf_designer_registry_structure_endpoint'),

    url(r'api/familylookup/(?P<reg_code>\w+)/?$', FamilyLookup.as_view(), name="family_lookup"),
    url(r'api/patientlookup/(?P<reg_code>\w+)/?$', PatientLookup.as_view(), name="patient_lookup"),
    # ---- Look-ups URLs -----------------------
    url(r"^lookup/username/(?P<username>[\w.%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4})/?$",
        UsernameLookup.as_view(), name="lookup_username"),

    url(r"^lookup/recaptcha/?$",
        RecaptchaValidator.as_view(), name="recaptcha_validator"),
    # -------------------------------------------

    url(r'^(?P<registry_code>\w+)/register/?$',
        RdrfRegistrationView.as_view(),
        name='registration_register'),
    url(r'^register/complete/?$',
        TemplateView.as_view(
            template_name='registration/registration_complete.html'),
        name='registration_complete'),
    url(r'^register/closed/?$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'),
        name='registration_disallowed'),
    url(r'^activate/complete/?$',
        TemplateView.as_view(
            template_name='registration/activation_complete.html'),
        name='registration_activation_complete'),

    url(r'^activate/(?P<activation_key>\w+)/?$',
        ActivationView.as_view(),
        name='registration_activate'),

    url(r'^i18n/', include('django.conf.urls.i18n')),
]
