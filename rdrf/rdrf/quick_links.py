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
    Users = QuickLink("admin:groups_customuser_changelist", 'Users')
    QuestionnaireResponses = QuickLink("admin:rdrf_questionnaireresponse_changelist", "Questionnaire Responses")
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
    PermissibleValueGroups = QuickLink("admin:rdrf_cdepermittedvaluegroup_changelist", "Permissible Value Groups", True)
    PermissibleValues = QuickLink("admin:rdrf_cdepermittedvalue_changelist", "Permissible Values", True)
    ConsentSections = QuickLink("admin:rdrf_consentsection_changelist", "Consent Sections", True)
    Importer = QuickLink("import_registry", "Importer", True)
    
    DATA_ENTRY = oset([PatientsListing])
    WORKING_GROUPS = oset([WorkingGroups])
    DOCTORS = oset([Doctors])
    REPORTING = oset([Reports])
    USER_MANAGEMENT = oset([Users])
    GENETIC_BOOKKEEPING = oset([Genes, Laboratories])
    REGISTRY_DESIGN = oset([Registries, RegistryForms, Sections, DataElements, PermissibleValueGroups,
                            PermissibleValues, ConsentSections, Importer])

    WORKING_GROUP_STAFF = DATA_ENTRY | DOCTORS
    WORKING_GROUP_CURATORS = DATA_ENTRY | DOCTORS | REPORTING | USER_MANAGEMENT

    GENETIC_STAFF = DATA_ENTRY | DOCTORS
    GENETIC_CURATORS = DATA_ENTRY | DOCTORS | REPORTING | GENETIC_BOOKKEEPING

    CLINICIAN = DATA_ENTRY | DOCTORS

    ALL = DATA_ENTRY | DOCTORS | REPORTING | USER_MANAGEMENT | GENETIC_BOOKKEEPING | REGISTRY_DESIGN | WORKING_GROUPS
