from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from rdrf.datastructures import OrderedSet as oset

class QuickLink(object):
    def __init__(self, url_name, text):
        self.url = reverse(url_name)
        self.text = _(text)


class QuickLinks(object):
    """
    A convenience class to make it easy to see what links are provided to
    users on the "Home" screen
    """
    PatientsListing = QuickLink("admin:patients_patient_changelist", "Patient List")
    Reports = QuickLink("reports", "Reports")
    Users = QuickLink("admin:groups_customuser_changelist", 'Users')
    QuestionnaireResponses = QuickLink("admin:rdrf_questionnaireresponse_changelist", "Questionnaire Responses")
    Doctors = QuickLink("admin:patients_doctor_changelist", "Doctors")
    # Genetic Staff
    Genes = QuickLink("admin:genetic_gene_changelist", "Genes")
    Laboratories = QuickLink("admin:genetic_laboratory_changelist", "Laboratories")

    # Admin only
    Registries = QuickLink("admin:rdrf_registry_changelist", "Registries")
    RegistryForms = QuickLink("admin:rdrf_registryform_changelist", "Registry Form")
    Sections = QuickLink("admin:rdrf_section_changelist", "Sections")
    DataElements = QuickLink("admin:rdrf_commondataelement_changelist", "Data Elements")
    PermissibleValueGroups = QuickLink("admin:rdrf_cdepermittedvaluegroup_changelist", "Permissible Value Groups")
    PermissibleValues = QuickLink("admin:rdrf_cdepermittedvalue_changelist", "Permissible Values")

    DATA_ENTRY = oset([PatientsListing])
    DOCTORS = oset([Doctors])
    REPORTING = oset([Reports])
    USER_MANAGEMENT = oset([Users])
    GENETIC_BOOKKEEPING = oset([Genes, Laboratories])
    REGISTRY_DESIGN = oset([Registries, RegistryForms, Sections, DataElements, PermissibleValueGroups,
                            PermissibleValues])

    WORKING_GROUP_STAFF = DATA_ENTRY | DOCTORS
    WORKING_GROUP_CURATORS = DATA_ENTRY | DOCTORS | REPORTING | USER_MANAGEMENT

    GENETIC_STAFF = DATA_ENTRY | DOCTORS
    GENETIC_CURATORS = DATA_ENTRY | DOCTORS | REPORTING | GENETIC_BOOKKEEPING

    CLINICIAN = DATA_ENTRY | DOCTORS

    ALL = DATA_ENTRY | DOCTORS | REPORTING | USER_MANAGEMENT | GENETIC_BOOKKEEPING | REGISTRY_DESIGN
