from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from operator import attrgetter

from rdrf.datastructures import OrderedSet
from registry.groups import GROUPS as RDRF_GROUPS

import logging

logger = logging.getLogger(__name__)


class QuickLink(object):

    def __init__(self, url_name, text, admin_link=False, glyph_icon="glyphicon-minus"):
        self.url = reverse(url_name)
        self.text = _(text)
        self.glyph_icon = glyph_icon
        self.admin_link = admin_link

    def getText(item):
        return item.text


# Non-admin quick links
PatientsListing = QuickLink("patientslisting", "Patient List")
Reports = QuickLink("reports", "Reports")
QuestionnaireResponses = QuickLink("admin:rdrf_questionnaireresponse_changelist", _("Questionnaire Responses"))
Doctors = QuickLink("admin:patients_doctor_changelist", _("Doctors"))
Genes = QuickLink("admin:genetic_gene_changelist", _("Genes"))
Laboratories = QuickLink("admin:genetic_laboratory_changelist", _("Laboratories"))

# Admin only quick links
Explorer = QuickLink("explorer_main", "Explorer", True)
Users = QuickLink("admin:groups_customuser_changelist", 'Users', True)
WorkingGroups = QuickLink("admin:groups_workinggroup_changelist", _("Working Groups"), True)
Registries = QuickLink("admin:rdrf_registry_changelist", _("Registries"), True)
RegistryForms = QuickLink("admin:rdrf_registryform_changelist", _("Registry Forms"), True)
Sections = QuickLink("admin:rdrf_section_changelist", _("Registry Sections"), True)
DataElements = QuickLink("admin:rdrf_commondataelement_changelist", _("Registry Common Data Elements"), True)
PermissibleValueGroups = QuickLink("admin:rdrf_cdepermittedvaluegroup_changelist",
                                   _("Registry Permissible Value Groups"), True)
PermissibleValues = QuickLink("admin:rdrf_cdepermittedvalue_changelist", _("Registry Permissible Values"), True)
ConsentSections = QuickLink("admin:rdrf_consentsection_changelist", _("Registry Consent Sections"), True)
ConsentValues = QuickLink("admin:patients_consentvalue_changelist", _("Registry Consent Values"), True)
DemographicsFields = QuickLink("admin:rdrf_demographicfields_changelist", _("Registry Demographics Fields"), True)
Importer = QuickLink("import_registry", _("Importer"), True)
Groups = QuickLink("admin:auth_group_changelist", _("Groups"), True)
NextOfKinRelationship = QuickLink("admin:patients_nextofkinrelationship_changelist",
                                  _("Next of Kin Relationship"), True)
CdePolicy = QuickLink("admin:rdrf_cdepolicy_changelist", _("Registry Common Data Elements Policy"), True)
States = QuickLink("admin:patients_state_changelist", _("States"), True)
ClinicianOther = QuickLink("admin:patients_clinicianother_changelist", _("Other Clinicians"), True)
EmailNotification = QuickLink("admin:rdrf_emailnotification_changelist", _("Email Notifications"), True)
EmailTemplate = QuickLink("admin:rdrf_emailtemplate_changelist", _("Email Templates"), True)
EmailNotificationHistory = QuickLink("admin:rdrf_emailnotificationhistory_changelist",
                                     _("Email Notifications History"), True)
RegistrationProfiles = QuickLink("admin:registration_registrationprofile_changelist", _("Registration Profiles"), True)
LoginLog = QuickLink("admin:useraudit_loginlog_changelist", _("User Login Log"), True)
FailedLoginLog = QuickLink("admin:useraudit_failedloginlog_changelist", _("User Failed Login Log"), True)
LoginAttempts = QuickLink("admin:useraudit_loginattempt_changelist", _("User Login Attempts Log"), True)
IPRestrictRangeGroup = QuickLink("admin:iprestrict_rangebasedipgroup_changelist", _("IP Restrict Ranges"), True)
IPRestrictGeoGroup = QuickLink("admin:iprestrict_locationbasedipgroup_changelist", _("IP Restrict Geolocations"), True)
IPRestrictRule = QuickLink("admin:iprestrict_rule_changelist", _("IP Restrict Rules"), True)
Sites = QuickLink("admin:sites_site_changelist", _("Sites"), True)
ParentGuardian = QuickLink("admin:patients_parentguardian_changelist", _("Parents/Guardians"), True)
ContextFormGroups = QuickLink("admin:rdrf_contextformgroup_changelist", "Registry Context Form Groups", True)
#FamilyLinkage = QuickLink("family_linkage", "Family Linkage")

# Ordered sets of related quick links
IP_RESTRICT = OrderedSet([IPRestrictRangeGroup, IPRestrictGeoGroup, IPRestrictRule])
DATA_ENTRY = OrderedSet([PatientsListing, ClinicianOther])
WORKING_GROUPS = OrderedSet([WorkingGroups])
DOCTORS = OrderedSet([Doctors])
REPORTING = OrderedSet([Reports])
AUDITING = OrderedSet([LoginLog, FailedLoginLog, LoginAttempts])
USER_MANAGEMENT = OrderedSet([Users])
GENETIC_BOOKKEEPING = OrderedSet([Genes, Laboratories])
REGISTRY_DESIGN = [Registries,
                   RegistryForms,
                   Sections,
                   DataElements,
                   CdePolicy,
                   PermissibleValueGroups,
                   PermissibleValues,
                   ConsentSections,
                   ConsentValues,
                   # Groups,
                   Importer,
                   Explorer,
                   DemographicsFields,
                   # NextOfKinRelationship,
                   RegistrationProfiles,
                   ContextFormGroups,
                   # EmailNotification,
                   # EmailTemplate,
                   # EmailNotificationHistory,
                   # Sites,
                   # ParentGuardian
                   ]
STATE_MANAGEMENT = OrderedSet([States])
QUESTIONNAIRE_HANDLING = OrderedSet([QuestionnaireResponses])

# Ordered sets of quick links defining our user groups
WORKING_GROUP_STAFF = sorted(DATA_ENTRY, key=attrgetter('text'))
WORKING_GROUP_CURATORS = sorted(DATA_ENTRY | REPORTING | USER_MANAGEMENT |
                                QUESTIONNAIRE_HANDLING, key=attrgetter('text'))
GENETIC_STAFF = sorted(DATA_ENTRY, key=attrgetter('text'))
GENETIC_CURATORS = sorted(DATA_ENTRY | GENETIC_BOOKKEEPING, key=attrgetter('text'))
CLINICIAN = sorted(DATA_ENTRY | QUESTIONNAIRE_HANDLING, key=attrgetter('text'))
ALL = sorted(
    # IP_RESTRICT |
    DATA_ENTRY |
    DOCTORS |
    REPORTING |
    # USER_MANAGEMENT |
    # AUDITING |
    # GENETIC_BOOKKEEPING |
    REGISTRY_DESIGN |
    # WORKING_GROUPS |
    QUESTIONNAIRE_HANDLING    # STATE_MANAGEMENT
    , key=attrgetter('text'))


class QuickLinks(object):
    """
    A convenience class to make it easy to see what links are provided to
    users on the "Home" screen
    """

    # map RDRF user groups to quick links menu sets
    switcher = {
        RDRF_GROUPS.PATIENTS: OrderedSet(),
        RDRF_GROUPS.PARENTS: OrderedSet(),
        RDRF_GROUPS.CLINICAL: CLINICIAN,
        RDRF_GROUPS.GENETIC_STAFF: GENETIC_STAFF,
        RDRF_GROUPS.GENETIC_CURATOR: GENETIC_CURATORS,
        RDRF_GROUPS.WORKING_GROUP_STAFF: WORKING_GROUP_STAFF,
        RDRF_GROUPS.WORKING_GROUP_CURATOR: WORKING_GROUP_CURATORS,
        RDRF_GROUPS.ALL: ALL,
    }

    @staticmethod
    def links(groups):
        rval = OrderedSet()
        for group in groups:
            rval = rval | QuickLinks.switcher.get(group.lower(), OrderedSet())
        return sorted(rval, key=attrgetter('text'))
