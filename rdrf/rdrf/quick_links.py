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
        "admin:rdrf_questionnaireresponse_changelist", "Questionnaire Responses")
    Doctors = QuickLink("admin:patients_doctor_changelist", "Doctors")
    # Genetic Staff
    Genes = QuickLink("admin:genetic_gene_changelist", "Genes")
    Laboratories = QuickLink("admin:genetic_laboratory_changelist", "Laboratories")
    WorkingGroups = QuickLink("admin:groups_workinggroup_changelist", "Working Groups")

    # Admin only
    Registries = QuickLink("admin:rdrf_registry_changelist", "Registries", True)
    RegistryForms = QuickLink("admin:rdrf_registryform_changelist", "Registry Form", True)
    Sections = QuickLink("admin:rdrf_section_changelist", "Sections", True)
    DataElements = QuickLink("admin:rdrf_commondataelement_changelist", "Data Elements", True)
    PermissibleValueGroups = QuickLink(
        "admin:rdrf_cdepermittedvaluegroup_changelist", "Permissible Value Groups", True)
    PermissibleValues = QuickLink(
        "admin:rdrf_cdepermittedvalue_changelist", "Permissible Values", True)
    ConsentSections = QuickLink(
        "admin:rdrf_consentsection_changelist", "Consent Sections", True)
    ConsentValues = QuickLink(
        "admin:patients_consentvalue_changelist", "Consent Values", False)
    DemographicsFields = QuickLink(
        "admin:rdrf_demographicfields_changelist", "Demographics Fields", True)
    Importer = QuickLink("import_registry", "Importer", True)
    Groups = QuickLink("admin:auth_group_changelist", "Groups", True)
    NextOfKinRelationship = QuickLink(
        "admin:patients_nextofkinrelationship_changelist", "Next of Kin Relationship", True)
    CdePolicy = QuickLink("admin:rdrf_cdepolicy_changelist", "CDE Policy", True)

    DATA_ENTRY = oset([
        PatientsListing,
    ])
    WORKING_GROUPS = oset([WorkingGroups])
    DOCTORS = oset([Doctors])
    REPORTING = oset([Reports])
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
                            NextOfKinRelationship])

    QUESTIONNAIRE_HANDLING = oset([QuestionnaireResponses])

    WORKING_GROUP_STAFF = DATA_ENTRY

    WORKING_GROUP_CURATORS = DATA_ENTRY | REPORTING | USER_MANAGEMENT | QUESTIONNAIRE_HANDLING

    GENETIC_STAFF = DATA_ENTRY
    GENETIC_CURATORS = DATA_ENTRY | GENETIC_BOOKKEEPING

    CLINICIAN = DATA_ENTRY | QUESTIONNAIRE_HANDLING

    ALL = DATA_ENTRY | DOCTORS | REPORTING | USER_MANAGEMENT | GENETIC_BOOKKEEPING | REGISTRY_DESIGN | WORKING_GROUPS | QUESTIONNAIRE_HANDLING
