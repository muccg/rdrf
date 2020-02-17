from collections import OrderedDict
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.urls.exceptions import NoReverseMatch
from django.conf import settings
from rdrf.system_role import SystemRoles

from registry.groups import GROUPS as RDRF_GROUPS

import logging

logger = logging.getLogger(__name__)


class QuickLink(object):

    def __init__(self, url, text):
        self.url = url
        self.translation = _(text)
        self.text = text

    def get_text(self, item):
        return item.text


class Links:
    """
    All links that can appear in menus are defined.
    Links are also grouped into related functional areas to make for easier assignment to menus
    """

    if settings.SYSTEM_ROLE in (SystemRoles.NORMAL, SystemRoles.CIC_DEV, SystemRoles.CIC_CLINICAL):
        PatientsListing = QuickLink(reverse("patientslisting"), _("Patient List"))
        Reports = QuickLink(reverse("reports"), _("Reports"))
        QuestionnaireResponses = QuickLink(reverse("admin:rdrf_questionnaireresponse_changelist"),
                                           _("Questionnaire Responses"))
        Doctors = QuickLink(reverse("admin:patients_doctor_changelist"), _("Doctors"))
        ArchivedPatients = QuickLink(
            reverse("admin:patients_archivedpatient_changelist"),
            _("Archived Patients"))
        Genes = QuickLink(reverse("admin:genetic_gene_changelist"), _("Genes"))
        Laboratories = QuickLink(reverse("admin:genetic_laboratory_changelist"), _("Laboratories"))
        Explorer = QuickLink(reverse("rdrf:explorer_main"), _("Explorer"))
        Users = QuickLink(reverse("admin:groups_customuser_changelist"), _('Users'))
        WorkingGroups = QuickLink(
            reverse("admin:groups_workinggroup_changelist"),
            _("Working Groups"))
        Registries = QuickLink(reverse("admin:rdrf_registry_changelist"), _("Registries"))

        Importer = QuickLink(reverse("import_registry"), _("Importer"))
        Groups = QuickLink(reverse("admin:auth_group_changelist"), _("Groups"))
        NextOfKinRelationship = QuickLink(
            reverse("admin:patients_nextofkinrelationship_changelist"),
            _("Next of Kin Relationship"))
        States = QuickLink(reverse("admin:patients_state_changelist"), _("States"))
        ClinicianOther = QuickLink(
            reverse("admin:patients_clinicianother_changelist"),
            _("Other Clinicians"))
        EmailNotification = QuickLink(
            reverse("admin:rdrf_emailnotification_changelist"),
            _("Email Notifications"))
        EmailTemplate = QuickLink(
            reverse("admin:rdrf_emailtemplate_changelist"),
            _("Email Templates"))
        EmailNotificationHistory = QuickLink(
            reverse("admin:rdrf_emailnotificationhistory_changelist"),
            _("Email Notifications History"))
        RegistrationProfiles = QuickLink(
            reverse("admin:registration_registrationprofile_changelist"),
            _("Registration Profiles"))
        LoginLog = QuickLink(reverse("admin:useraudit_loginlog_changelist"), _("User Login Log"))
        FailedLoginLog = QuickLink(
            reverse("admin:useraudit_failedloginlog_changelist"),
            _("User Failed Login Log"))
        LoginAttempts = QuickLink(
            reverse("admin:useraudit_loginattempt_changelist"),
            _("User Login Attempts Log"))
        IPRestrictRangeGroup = QuickLink(
            reverse("admin:iprestrict_rangebasedipgroup_changelist"),
            _("IP Restrict Ranges"))
        IPRestrictGeoGroup = QuickLink(reverse("admin:iprestrict_locationbasedipgroup_changelist"),
                                       _("IP Restrict Geolocations"))
        IPRestrictRule = QuickLink(
            reverse("admin:iprestrict_rule_changelist"),
            _("IP Restrict Rules"))
        Sites = QuickLink(reverse("admin:sites_site_changelist"), _("Sites"))
        ParentGuardian = QuickLink(
            reverse("admin:patients_parentguardian_changelist"),
            _("Parents/Guardians"))

        Doctors = QuickLink(reverse("admin:patients_doctor_changelist"), _("Doctors"))
        DemographicsFields = QuickLink(
            reverse("admin:rdrf_demographicfields_changelist"),
            _("Registry Demographics Fields"))
        ConsentRules = QuickLink(reverse("admin:rdrf_consentrule_changelist"), _("Consent Rules"))
        Reviews = QuickLink(reverse("admin:rdrf_review_changelist"), _("Reviews"))
        PatientReviews = QuickLink(reverse("admin:rdrf_patientreview_changelist"), _("Patient Reviews"))
        Verifications = QuickLink(reverse("admin:rdrf_verification_changelist"), _("Verifications"))
        Custom_Actions = QuickLink(reverse("admin:rdrf_customaction_changelist"), _("Custom Actions"))

    if settings.SYSTEM_ROLE in (SystemRoles.CIC_DEV, SystemRoles.CIC_PROMS, SystemRoles.CIC_CLINICAL):
        Surveys = QuickLink(reverse("admin:rdrf_survey_changelist"), _("Surveys"))
        SurveyAssignments = QuickLink(reverse("admin:rdrf_surveyassignment_changelist"), _("Survey Assignments"))
        SurveyRequest = QuickLink(reverse("admin:rdrf_surveyrequest_changelist"), _("Survey Request"))

    if settings.DESIGN_MODE:
        Registries = QuickLink(reverse("admin:rdrf_registry_changelist"), _("Registries"))
        RegistryForms = QuickLink(
            reverse("admin:rdrf_registryform_changelist"),
            _("Registry Forms"))
        Sections = QuickLink(reverse("admin:rdrf_section_changelist"), _("Registry Sections"))
        DataElements = QuickLink(
            reverse("admin:rdrf_commondataelement_changelist"),
            _("Registry Common Data Elements"))
        PermissibleValueGroups = QuickLink(
            reverse("admin:rdrf_cdepermittedvaluegroup_changelist"),
            _("Registry Permissible Value Groups"))
        PermissibleValues = QuickLink(
            reverse("admin:rdrf_cdepermittedvalue_changelist"),
            _("Registry Permissible Values"))
        ConsentSections = QuickLink(
            reverse("admin:rdrf_consentsection_changelist"),
            _("Registry Consent Sections"))
        ConsentValues = QuickLink(
            reverse("admin:patients_consentvalue_changelist"),
            _("Registry Consent Values"))
        CdePolicy = QuickLink(
            reverse("admin:rdrf_cdepolicy_changelist"),
            _("Registry Common Data Elements Policy"))
        ContextFormGroups = QuickLink(
            reverse("admin:rdrf_contextformgroup_changelist"),
            _("Registry Context Form Groups"))

    if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
        Importer = QuickLink(reverse("import_registry"), _("Importer"))
        Users = QuickLink(reverse("admin:groups_customuser_changelist"), _('Users'))

    if settings.SYSTEM_ROLE in (SystemRoles.NORMAL, SystemRoles.CIC_DEV, SystemRoles.CIC_CLINICAL):
        # related links are grouped or convenience
        AUDITING = {
            LoginLog.text: LoginLog,
            FailedLoginLog.text: FailedLoginLog,
            LoginAttempts.text: LoginAttempts
        }
        DATA_ENTRY = {
            PatientsListing.text: PatientsListing,
        }
        EMAIL = {
            EmailNotification.text: EmailNotification,
            EmailTemplate.text: EmailTemplate,
            EmailNotificationHistory.text: EmailNotificationHistory,
        }
        GENETIC = {
            Genes.text: Genes,
            Laboratories.text: Laboratories,
        }
        IP_RESTRICT = {
            IPRestrictRangeGroup.text: IPRestrictRangeGroup,
            IPRestrictGeoGroup.text: IPRestrictGeoGroup,
            IPRestrictRule.text: IPRestrictRule
        }
        if settings.DESIGN_MODE:
            OTHER = {
                Sites.text: Sites,
                Groups.text: Groups,
                Importer.text: Importer,
                DemographicsFields.text: DemographicsFields,
                NextOfKinRelationship.text: NextOfKinRelationship,
                ArchivedPatients.text: ArchivedPatients,
                ConsentRules.text: ConsentRules,
                Reviews.text: Reviews,
                PatientReviews.text: PatientReviews,
                Verifications.text: Verifications,
                Custom_Actions.text: Custom_Actions,
            }
        else:
            OTHER = {
                Sites.text: Sites,
                Groups.text: Groups,
                DemographicsFields.text: DemographicsFields,
                Importer.text: Importer,
                NextOfKinRelationship.text: NextOfKinRelationship,
                ArchivedPatients.text: ArchivedPatients,
                ConsentRules.text: ConsentRules,
                Reviews.text: Reviews,
                PatientReviews.text: PatientReviews,
                Verifications.text: Verifications,
                Custom_Actions.text: Custom_Actions,
            }
        EXPLORER = {
            Explorer.text: Explorer,
        }
        if settings.DESIGN_MODE:
            REGISTRY_DESIGN = {
                Registries.text: Registries,
                RegistryForms.text: RegistryForms,
                Sections.text: Sections,
                DataElements.text: DataElements,
                CdePolicy.text: CdePolicy,
                PermissibleValueGroups.text: PermissibleValueGroups,
                PermissibleValues.text: PermissibleValues,
                ConsentSections.text: ConsentSections,
                ConsentValues.text: ConsentValues,
                ContextFormGroups.text: ContextFormGroups,
            }
        REPORTING = {
            Reports.text: Reports,
        }
        STATE_MANAGEMENT = {
            States.text: States
        }
        WORKING_GROUPS = {
            WorkingGroups.text: WorkingGroups,
        }
        # When enabled, doctors links
        ENABLED_DOCTORS = {
            Doctors.text: Doctors,
        }

        # When enabled, questionnaire links
        ENABLED_QUESTIONNAIRE = {
            QuestionnaireResponses.text: QuestionnaireResponses,
        }
        # When enabled, registration links
        ENABLED_REGISTRATION = {
            ParentGuardian.text: ParentGuardian,
            RegistrationProfiles.text: RegistrationProfiles,
            ClinicianOther.text: ClinicianOther
        }

        # only appear if related registry specific feature is set
        # Populated at runtime
        CONSENT = {}
        DOCTORS = {}
        FAMILY_LINKAGE = {}
        PERMISSIONS = {}
        QUESTIONNAIRE = {}
        REGISTRATION = {}
        VERIFICATION = {}

    if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
        OTHER = {
            Importer.text: Importer,
        }
        REGISTRATION = {}
        PERMISSIONS = {}

    USER_MANAGEMENT = {
        Users.text: Users,
    }

    if settings.SYSTEM_ROLE in (SystemRoles.CIC_PROMS, SystemRoles.CIC_DEV, SystemRoles.CIC_CLINICAL):
        PROMS = {
            Surveys.text: Surveys,
            SurveyAssignments.text: SurveyAssignments,
            SurveyRequest.text: SurveyRequest,
        }

    if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
        if settings.DESIGN_MODE:
            REGISTRY_DESIGN = {
                Registries.text: Registries,
                RegistryForms.text: RegistryForms,
                Sections.text: Sections,
                DataElements.text: DataElements,
                CdePolicy.text: CdePolicy,
                PermissibleValueGroups.text: PermissibleValueGroups,
                PermissibleValues.text: PermissibleValues,
                ConsentSections.text: ConsentSections,
                ConsentValues.text: ConsentValues,
                ContextFormGroups.text: ContextFormGroups,
            }


class MenuConfig(object):
    """
    A singleton to store our Menu config
    Source https://python-3-patterns-idioms-test.readthedocs.io/
    """

    class MenuConfigInner:

        def __init__(self, arg='default'):
            self.val = arg

        def __str__(self):
            return repr(self) + self.val

    _instance = None

    def __new__(cls):
        if not MenuConfig._instance:
            MenuConfig._instance = MenuConfig.MenuConfigInner()
        return MenuConfig._instance

    def __getattr__(self, name):
        return getattr(self._instance, name)

    def __setattr__(self, name):
        return setattr(self._instance, name)


class QuickLinks(object):
    """
    A convenience class to make it easy to see what links are provided to users on the "Home" screen
    """

    def _build_menu(self):
        # Main menu per user type
        design_menus = {}

        if settings.DESIGN_MODE:
            design_menus = {
                **Links.REGISTRY_DESIGN,
            }

        if settings.SYSTEM_ROLE in (SystemRoles.CIC_DEV, SystemRoles.NORMAL, SystemRoles.CIC_CLINICAL):
            normal_menus = {
                **Links.AUDITING,
                **Links.CONSENT,
                **Links.DATA_ENTRY,
                **Links.DOCTORS,
                **Links.EMAIL,
                **Links.FAMILY_LINKAGE,
                **Links.GENETIC,
                **Links.IP_RESTRICT,
                **Links.OTHER,
                **Links.PERMISSIONS,
                **Links.QUESTIONNAIRE,
                **Links.REGISTRATION,
                **Links.REPORTING,
                **Links.STATE_MANAGEMENT,
                **Links.USER_MANAGEMENT,
                **Links.WORKING_GROUPS,
            }
            MenuConfig().patient = {}

            MenuConfig().parent = {}

            if settings.SYSTEM_ROLE in (SystemRoles.CIC_DEV, SystemRoles.CIC_CLINICAL):
                if settings.DESIGN_MODE:
                    design_menus.update({**Links.PROMS, })
                else:
                    normal_menus.update({**Links.PROMS, })

            MenuConfig().working_group_staff = {
                **Links.DATA_ENTRY
            }

            MenuConfig().working_group_curator = {
                **Links.CONSENT,
                **Links.DATA_ENTRY,
                **Links.DOCTORS,
                **Links.REPORTING,
                **Links.USER_MANAGEMENT,
                **Links.QUESTIONNAIRE,
            }

            MenuConfig().genetic_staff = {
                **Links.DATA_ENTRY
            }

            MenuConfig().genetic_curator = {
                **Links.DATA_ENTRY,
                **Links.GENETIC
            }

            MenuConfig().clinical = {
                **Links.DATA_ENTRY,
                **Links.QUESTIONNAIRE,
                **Links.VERIFICATION,
            }

            # Super user has combined menu of all other users
            MenuConfig().super_user = {
                **MenuConfig().working_group_staff,
                **MenuConfig().working_group_curator,
                **MenuConfig().genetic_staff,
                **MenuConfig().genetic_curator,
                **MenuConfig().clinical,
            }

        # settings menu
            MenuConfig().settings = {
                **Links.AUDITING,
                **Links.DOCTORS,
                **Links.EXPLORER,
                **Links.FAMILY_LINKAGE,
                **Links.PERMISSIONS,
                **Links.REGISTRATION,
            }

            # menu with everything, used for the admin page
            if not settings.DESIGN_MODE:
                MenuConfig().all = normal_menus
            else:
                design_menus.update(normal_menus)
                MenuConfig().all = design_menus

        if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
            MenuConfig().settings = {
                **Links.PERMISSIONS,
                **Links.REGISTRATION,
            }
            proms_menus = {
                **Links.PROMS,
                **Links.USER_MANAGEMENT,
                **Links.OTHER,
            }
            # menu with everything, used for the admin page
            if settings.DESIGN_MODE:
                design_menus.update(proms_menus)
                MenuConfig().all = design_menus
            else:
                MenuConfig().all = proms_menus

    def _group_links(self, group):
        # map RDRF user groups to quick links menu sets
        switcher = {
            RDRF_GROUPS.PATIENT: MenuConfig().patient,
            RDRF_GROUPS.PARENT: MenuConfig().parent,
            RDRF_GROUPS.CLINICAL: MenuConfig().clinical,
            RDRF_GROUPS.GENETIC_STAFF: MenuConfig().genetic_staff,
            RDRF_GROUPS.GENETIC_CURATOR: MenuConfig().genetic_curator,
            RDRF_GROUPS.WORKING_GROUP_STAFF: MenuConfig().working_group_staff,
            RDRF_GROUPS.WORKING_GROUP_CURATOR: MenuConfig().working_group_curator,
            RDRF_GROUPS.SUPER_USER: MenuConfig().super_user,
        }
        return switcher.get(group.lower(), [])

    def __init__(self, registries):
        self._registries = registries

        # enable dynamic links and build the menu
        self._consent_links()
        self._doctors_link()
        self._family_linkage_links()
        self._questionnaire_links()
        self._permission_matrix_links()
        self._registration_links()
        self._verification_links()
        self._custom_action_links()
        self._build_menu()

    def _per_registry_links(self, label, url, feature=None):
        # build any per registry links that require the registry code as a param
        rval = {}
        for registry in self._registries:
            # don't provide per registry links to a registy that doesn't support feature
            if feature and not registry.has_feature(feature):
                continue

            try:
                text = label + ' (' + registry.name + ')'
                qlink = QuickLink(reverse(url, args=(registry.code,)), _(text))
                rval[text] = qlink
            except NoReverseMatch:
                logging.exception(
                    'No reverse url for {0} with registry code {1}'.format(
                        url, registry.code))
        return rval

    def _registration_links(self):
        # enable registration links if any registry uses registration
        for registry in self._registries:
            # don't provide per registry links to a registy that doesn't support feature
            if registry.has_feature('registration'):
                Links.REGISTRATION = Links.ENABLED_REGISTRATION
                break

    def _doctors_link(self):
        for registry in self._registries:
            if registry.has_feature("doctors_list"):
                Links.DOCTORS = Links.ENABLED_DOCTORS
                break

    def _questionnaire_links(self):
        # enable questionnaire links if any registry uses questionnaires
        links = self._per_registry_links('Questionnaires', 'questionnaire', 'questionnaires')

        # special case: if we have questionnaires enabled, we enable questionnaire links
        if len(links) > 0:
            links = {**links, **Links.ENABLED_QUESTIONNAIRE}
        Links.QUESTIONNAIRE = links

    def _family_linkage_links(self):
        # enable family linkage links if any registry uses family linkage
        Links.FAMILY_LINKAGE = self._per_registry_links(
            'Family Linkage', 'family_linkage', 'family_linkage')

        # special case: if we have family linkage enabled, we enable doctors links
        if len(Links.FAMILY_LINKAGE) > 0:
            Links.DOCTORS = Links.ENABLED_DOCTORS

    def _verification_links(self):
        Links.VERIFICATION = self._per_registry_links('Verifications',
                                                      'verifications_list',
                                                      'verification')

    def _custom_action_links(self):
        Links.CUSTOM_ACTIONS = self._per_registry_links('Custom Actions',
                                                        'customactions_list',
                                                        'custom_actions')

    def _permission_matrix_links(self):
        if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
            return {}
        # enable permission links
        Links.PERMISSIONS = self._per_registry_links('Permissions', 'permission_matrix')

    def _consent_links(self):
        if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
            return {}
        # enable consent links
        Links.CONSENT = self._per_registry_links('Consents', 'consent_list')

    def menu_links(self, groups):
        # get links for the 'menu' menu
        links = {}
        if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
            return {}
        for group in groups:
            links = {**links, **self._group_links(group.lower())}
        return list(OrderedDict(sorted(links.items())).values())

    def settings_links(self):
        # get links for the 'settings' menu
        if settings.SYSTEM_ROLE == SystemRoles.CIC_PROMS:
            return {}
        links = MenuConfig().settings
        return OrderedDict(sorted(links.items())).values()

    def admin_page_links(self):
        # get links for the admin page
        links = MenuConfig().all
        return OrderedDict(sorted(links.items())).values()
