from collections import OrderedDict
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.urls.exceptions import NoReverseMatch

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

    PatientsListing = QuickLink(reverse("patientslisting"), "Patient List")
    Reports = QuickLink(reverse("reports"), "Reports")
    QuestionnaireResponses = QuickLink(reverse("admin:rdrf_questionnaireresponse_changelist"),
                                       "Questionnaire Responses")
    Doctors = QuickLink(reverse("admin:patients_doctor_changelist"), "Doctors")
    ArchivedPatients = QuickLink(reverse("admin:patients_archivedpatient_changelist"), "Archived Patients")
    Genes = QuickLink(reverse("admin:genetic_gene_changelist"), "Genes")
    Laboratories = QuickLink(reverse("admin:genetic_laboratory_changelist"), "Laboratories")
    Explorer = QuickLink(reverse("explorer_main"), "Explorer")
    Users = QuickLink(reverse("admin:groups_customuser_changelist"), 'Users')
    WorkingGroups = QuickLink(reverse("admin:groups_workinggroup_changelist"), "Working Groups")
    Registries = QuickLink(reverse("admin:rdrf_registry_changelist"), "Registries")
    RegistryForms = QuickLink(reverse("admin:rdrf_registryform_changelist"), "Registry Forms")
    Sections = QuickLink(reverse("admin:rdrf_section_changelist"), "Registry Sections")
    DataElements = QuickLink(reverse("admin:rdrf_commondataelement_changelist"), "Registry Common Data Elements")
    PermissibleValueGroups = QuickLink(reverse("admin:rdrf_cdepermittedvaluegroup_changelist"),
                                       "Registry Permissible Value Groups")
    PermissibleValues = QuickLink(reverse("admin:rdrf_cdepermittedvalue_changelist"), "Registry Permissible Values")
    ConsentSections = QuickLink(reverse("admin:rdrf_consentsection_changelist"), "Registry Consent Sections")
    ConsentValues = QuickLink(reverse("admin:patients_consentvalue_changelist"), "Registry Consent Values")
    DemographicsFields = QuickLink(reverse("admin:rdrf_demographicfields_changelist"), "Registry Demographics Fields")
    Importer = QuickLink(reverse("import_registry"), "Importer")
    Groups = QuickLink(reverse("admin:auth_group_changelist"), "Groups")
    NextOfKinRelationship = QuickLink(reverse("admin:patients_nextofkinrelationship_changelist"),
                                      "Next of Kin Relationship")
    CdePolicy = QuickLink(reverse("admin:rdrf_cdepolicy_changelist"), "Registry Common Data Elements Policy")
    States = QuickLink(reverse("admin:patients_state_changelist"), "States")
    ClinicianOther = QuickLink(reverse("admin:patients_clinicianother_changelist"), "Other Clinicians")
    EmailNotification = QuickLink(reverse("admin:rdrf_emailnotification_changelist"), "Email Notifications")
    EmailTemplate = QuickLink(reverse("admin:rdrf_emailtemplate_changelist"), "Email Templates")
    EmailNotificationHistory = QuickLink(reverse("admin:rdrf_emailnotificationhistory_changelist"),
                                         "Email Notifications History")
    RegistrationProfiles = QuickLink(reverse("admin:registration_registrationprofile_changelist"),
                                     "Registration Profiles")
    LoginLog = QuickLink(reverse("admin:useraudit_loginlog_changelist"), "User Login Log")
    FailedLoginLog = QuickLink(reverse("admin:useraudit_failedloginlog_changelist"), "User Failed Login Log")
    LoginAttempts = QuickLink(reverse("admin:useraudit_loginattempt_changelist"), "User Login Attempts Log")
    IPRestrictRangeGroup = QuickLink(reverse("admin:iprestrict_rangebasedipgroup_changelist"), "IP Restrict Ranges")
    IPRestrictGeoGroup = QuickLink(reverse("admin:iprestrict_locationbasedipgroup_changelist"),
                                   "IP Restrict Geolocations")
    IPRestrictRule = QuickLink(reverse("admin:iprestrict_rule_changelist"), "IP Restrict Rules")
    Sites = QuickLink(reverse("admin:sites_site_changelist"), "Sites")
    ParentGuardian = QuickLink(reverse("admin:patients_parentguardian_changelist"), "Parents/Guardians")
    ContextFormGroups = QuickLink(reverse("admin:rdrf_contextformgroup_changelist"), "Registry Context Form Groups")

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
    OTHER = {
            Sites.text: Sites,
            Groups.text: Groups,
            Importer.text: Importer,
            DemographicsFields.text: DemographicsFields,
            NextOfKinRelationship.text: NextOfKinRelationship,
            ArchivedPatients.text: ArchivedPatients,
            }
    EXPLORER = {
            Explorer.text: Explorer,
            }
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
    USER_MANAGEMENT = {
            Users.text: Users,
            }
    WORKING_GROUPS = {
            WorkingGroups.text: WorkingGroups,
            }

    # only appear if related registry specific feature is set
    # Populated at runtime
    CONSENT = {}
    DOCTORS = {}
    FAMILY_LINKAGE = {}
    PERMISSIONS = {}
    QUESTIONNAIRE = {}
    REGISTRATION = {}

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


class MenuConfig(object):
    """
    A singleton to store our Menu config
    Source https://python-3-patterns-idioms-test.readthedocs.io/
    """

    class __MenuConfig:

        def __init__(self, arg='default'):
            self.val = arg

        def __str__(self):
            return repr(self) + self.val

    _instance = None

    def __new__(cls):
        if not MenuConfig._instance:
            MenuConfig._instance = MenuConfig.__MenuConfig()
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
        MenuConfig().patient = {}

        MenuConfig().parent = {}

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
        MenuConfig().all = {
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
                **Links.REGISTRY_DESIGN,
                **Links.REPORTING,
                **Links.STATE_MANAGEMENT,
                **Links.USER_MANAGEMENT,
                **Links.WORKING_GROUPS,
                }

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
        self._family_linkage_links()
        self._questionnaire_links()
        self._permission_matrix_links()
        self._registration_links()
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
                qlink = QuickLink(reverse(url, args=(registry.code,)), text)
                rval[text] = qlink
            except NoReverseMatch:
                logging.exception('No reverse url for {0} with registry code {1}'.format(url, registry.code))
        return rval

    def _registration_links(self):
        # enable registration links if any registry uses registration
        for registry in self._registries:
            # don't provide per registry links to a registy that doesn't support feature
            if registry.has_feature('registration'):
                Links.REGISTRATION = Links.ENABLED_REGISTRATION
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
        Links.FAMILY_LINKAGE = self._per_registry_links('Family Linkage', 'family_linkage', 'family_linkage')

        # special case: if we have family linkage enabled, we enable doctors links
        if len(Links.FAMILY_LINKAGE) > 0:
            Links.DOCTORS = Links.ENABLED_DOCTORS

    def _permission_matrix_links(self):
        # enable permission links
        Links.PERMISSIONS = self._per_registry_links('Permissions', 'permission_matrix')

    def _consent_links(self):
        # enable consent links
        Links.CONSENT = self._per_registry_links('Consents', 'consent_list')

    def menu_links(self, groups):
        # get links for the 'menu' menu
        links = {}
        for group in groups:
            links = {**links, **self._group_links(group.lower())}
        return OrderedDict(sorted(links.items())).values()

    def settings_links(self):
        # get links for the 'settings' menu
        links = MenuConfig().settings
        return OrderedDict(sorted(links.items())).values()

    def admin_page_links(self):
        # get links for the admin page
        links = MenuConfig().all
        return OrderedDict(sorted(links.items())).values()
