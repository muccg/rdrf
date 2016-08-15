from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from rdrf.datastructures import OrderedSet as oset


class QuickLink(object):

    def __init__(self, url_name, text, admin_link=False, glyph_icon="glyphicon-minus"):
        self.url = reverse(url_name)
        self.text = _(text)
        self.glyph_icon = glyph_icon
        self.admin_link = admin_link


class QuickLinks(object):

    """
    A convenience class to make it easy to see what links are provided to
    users on the "Home" screen
    """
    PatientsListing = QuickLink("patientslisting", "Patient List")
    Reports = QuickLink("reports", "Reports")
    Explorer = QuickLink("explorer_main", "Explorer", True)
    Users = QuickLink("admin:groups_customuser_changelist", 'Users')
    QuestionnaireResponses = QuickLink(
        "admin:rdrf_questionnaireresponse_changelist", _("Questionnaire Responses"))
    Doctors = QuickLink("admin:patients_doctor_changelist", _("Doctors"))
    # Genetic Staff
    Genes = QuickLink("admin:genetic_gene_changelist", _("Genes"))
    Laboratories = QuickLink("admin:genetic_laboratory_changelist", _("Laboratories"))

    WorkingGroups = QuickLink("admin:groups_workinggroup_changelist", _("Working Groups"))

    # Admin only
    Registries = QuickLink("admin:rdrf_registry_changelist", _("Registries"), True)
    RegistryForms = QuickLink("admin:rdrf_registryform_changelist", _("Registry Form"), True)
    Sections = QuickLink("admin:rdrf_section_changelist", _("Sections"), True)
    DataElements = QuickLink("admin:rdrf_commondataelement_changelist", _("Data Elements"), True)
    PermissibleValueGroups = QuickLink(
        "admin:rdrf_cdepermittedvaluegroup_changelist", _("Permissible Value Groups"), True)
    PermissibleValues = QuickLink(
        "admin:rdrf_cdepermittedvalue_changelist", _("Permissible Values"), True)
    ConsentSections = QuickLink(
        "admin:rdrf_consentsection_changelist", _("Consent Sections"), True)
    ConsentValues = QuickLink(
        "admin:patients_consentvalue_changelist", _("Consent Values"), False)
    DemographicsFields = QuickLink(
        "admin:rdrf_demographicfields_changelist", _("Demographics Fields"), True)
    Importer = QuickLink("import_registry", _("Importer"), True)
    Groups = QuickLink("admin:auth_group_changelist", _("Groups"), True)
    NextOfKinRelationship = QuickLink(
        "admin:patients_nextofkinrelationship_changelist", _("Next of Kin Relationship"), True)
    CdePolicy = QuickLink("admin:rdrf_cdepolicy_changelist", _("CDE Policy"), True)
    States = QuickLink("admin:patients_state_changelist", _("States"))
    ClinicianOther = QuickLink("admin:patients_clinicianother_changelist", _("Other Clinicians"))
    EmailNotification = QuickLink("admin:rdrf_emailnotification_changelist", _("Email Notifications"), True)
    EmailTemplate = QuickLink("admin:rdrf_emailtemplate_changelist", _("Email Templates"), True)
    EmailNotificationHistory = QuickLink(
        "admin:rdrf_emailnotificationhistory_changelist", _("Email Notifications History"), True)
    RegistrationProfiles = QuickLink("admin:registration_registrationprofile_changelist",
                                     _("Registration Profiles"), True)

    LoginLog = QuickLink("admin:useraudit_loginlog_changelist", _("User Login Log"), True)
    FailedLoginLog = QuickLink("admin:useraudit_failedloginlog_changelist", _("User Failed Login Log"), True)
    LoginAttempts = QuickLink("admin:useraudit_loginattempt_changelist", _("User Login Attempts Log"), True)

    IPRestrictGroup = QuickLink("admin:iprestrict_ipgroup_changelist", _("IP Restrict Groups"), True)
    IPRestrictRule = QuickLink("admin:iprestrict_rule_changelist", _("IP Restrict Rules"), True)

    # Context Form Groups
    ContextFormGroups = QuickLink("admin:rdrf_contextformgroup_changelist", "Context Form Groups", True)

    #FamilyLinkage = QuickLink("family_linkage", "Family Linkage")
    IP_RESTRICT = oset([IPRestrictGroup, IPRestrictRule])

    DATA_ENTRY = oset([PatientsListing, ClinicianOther])
    WORKING_GROUPS = oset([WorkingGroups])
    DOCTORS = oset([Doctors])
    REPORTING = oset([Reports])
    AUDITING = oset([LoginLog, FailedLoginLog, LoginAttempts])
    USER_MANAGEMENT = oset([Users])
    GENETIC_BOOKKEEPING = oset([Genes, Laboratories])
    REGISTRY_DESIGN = oset([Registries,
                            RegistryForms,
                            Sections,
                            DataElements,
                            CdePolicy,
                            PermissibleValueGroups,
                            PermissibleValues,
                            ConsentSections,
                            ConsentValues,
                            Groups,
                            Importer,
                            Explorer,
                            DemographicsFields,
                            NextOfKinRelationship,
                            RegistrationProfiles,
                            ContextFormGroups,
                            EmailNotification,
                            EmailTemplate,
                            EmailNotificationHistory])

    QUESTIONNAIRE_HANDLING = oset([QuestionnaireResponses])

    WORKING_GROUP_STAFF = DATA_ENTRY

    WORKING_GROUP_CURATORS = DATA_ENTRY | REPORTING | USER_MANAGEMENT | QUESTIONNAIRE_HANDLING

    GENETIC_STAFF = DATA_ENTRY
    GENETIC_CURATORS = DATA_ENTRY | GENETIC_BOOKKEEPING

    CLINICIAN = DATA_ENTRY | QUESTIONNAIRE_HANDLING

    STATE_MANAGEMENT = oset([States])

    ALL = IP_RESTRICT | DATA_ENTRY | DOCTORS | REPORTING | USER_MANAGEMENT | AUDITING | GENETIC_BOOKKEEPING | REGISTRY_DESIGN | WORKING_GROUPS | QUESTIONNAIRE_HANDLING | STATE_MANAGEMENT
