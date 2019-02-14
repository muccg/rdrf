from collections import namedtuple
import django.apps as apps

from . import model_exporters, datagroup_exporters


class GroupDefinition(
    namedtuple(
        'GroupDefinition', [
            'name', 'dirname', 'datagroups', 'models'])):

    def __new__(cls, name, dirname, datagroups=(), models=()):
        return super(GroupDefinition, cls).__new__(cls, name, dirname, datagroups, models)

    @property
    def model_classes(self):
        return [apps.get_model(n) for n in self.models]


Catalogue = namedtuple('Catalogue', ['datagroups', 'models'])
ExportDefinition = namedtuple('ExportDefinition', ['type', 'exporters_catalogue', 'datagroups'])
ExportType = namedtuple('ExportType', ['code', 'name', 'includes'])


_MAIN_CATALOGUE = Catalogue(
    datagroup_exporters.catalogue,
    model_exporters.catalogue,
)

_CDE_GROUP = GroupDefinition(
    name='CDEs',
    dirname='CDE',
    models=(
        'rdrf.CDEPermittedValueGroup',
        'rdrf.CDEPermittedValue',
        'rdrf.CommonDataElement',
    ))

_REFDATA_GROUP = GroupDefinition(
    name='Reference Data',
    dirname='reference_data',
    models=(
        'genetic.Gene',
        'genetic.Laboratory',
        'genetic.Technique',

        'patients.State',
        'patients.NextOfKinRelationship',
        'patients.AddressType',
    ))

_USERS_GROUP = GroupDefinition(
    name='Users',
    dirname='users',
    models=(
        'groups.CustomUser',
    ))

_REGISTRY_DEF_GROUP = GroupDefinition(
    name='Registry Definition',
    dirname='registry_definition',
    models=(
        'rdrf.Section',  # because registry has a potentially non-null "PatientDataSection" ..
        'rdrf.Registry',
        'groups.WorkingGroup',
        'auth.Group',
        'rdrf.RegistryForm',
        'rdrf.CdePolicy',
        'rdrf.ConsentSection',
        'rdrf.ConsentQuestion',
        'rdrf.DemographicFields',
        'rdrf.EmailTemplate',
        'rdrf.Wizard',
        'explorer.Query',
        'rdrf.ContextFormGroup',
        'rdrf.ContextFormGroupItem',
    ))


class ExportTypes(object):
    CDES = ExportType('cdes', 'Common Data Elements', ())
    REFDATA = ExportType('refdata', 'Reference Data', ())
    REGISTRY_DEF = ExportType('registry_def', 'Registry Definition', (CDES, REFDATA))
    REGISTRY_WITH_DATA = ExportType(
        'registry', 'Registry Definition and Data', (CDES, REFDATA, REGISTRY_DEF))

    all_types = (CDES, REFDATA, REGISTRY_DEF, REGISTRY_WITH_DATA)

    registry_types = (REGISTRY_DEF, REGISTRY_WITH_DATA)
    registry_types_names = [t.name for t in registry_types]
    registry_types_codes = [t.code for t in registry_types]

    @classmethod
    def from_code(cls, code):
        for t in cls.all_types:
            if t.code == code:
                return t
        raise ValueError("Invalid export type code '%s'" % code)

    @classmethod
    def from_name(cls, name):
        for t in cls.all_types:
            if t.name == name:
                return t
        raise ValueError("Invalid export type name '%s'" % name)


# TODO this is far from ideal and quite a bit naive
# It is used to filter what to import if the user decides to request an import
# type that is a subset of the export file (ex. import CDES only from a
# Reference Data export)
# These dependencies between data groups should be declared in this file and
# the importer should deduce them from the definitions.
META_FILTERS = {
    ExportTypes.CDES: lambda m: m['name'] == 'CDEs',
    ExportTypes.REFDATA: lambda m: m['name'] == 'Reference Data',
    ExportTypes.REGISTRY_DEF: lambda m: m['name'] != 'Registry Data',
}


# Export definitons for different type of exports


CDE_EXPORT_DEFINITION = ExportDefinition(
    type=ExportTypes.CDES,
    exporters_catalogue=_MAIN_CATALOGUE,
    datagroups=(_CDE_GROUP,)
)

REFDATA_EXPORT_DEFINITION = ExportDefinition(
    type=ExportTypes.REFDATA,
    exporters_catalogue=_MAIN_CATALOGUE,
    datagroups=(_REFDATA_GROUP,)
)

REGISTRY_DEF_EXPORT_DEFINITION = ExportDefinition(
    type=ExportTypes.REGISTRY_DEF,
    exporters_catalogue=Catalogue(
        datagroup_exporters.catalogue,
        model_exporters.registry_catalogue,
    ),
    datagroups=(
        _REFDATA_GROUP,
        _CDE_GROUP,
        _REGISTRY_DEF_GROUP,
    ),
)

REGISTRY_WITH_DATA_EXPORT_DEFINITION = ExportDefinition(
    type=ExportTypes.REGISTRY_WITH_DATA,
    exporters_catalogue=Catalogue(
        datagroup_exporters.catalogue,
        model_exporters.registry_catalogue,
    ),
    datagroups=(
        _REFDATA_GROUP,
        _CDE_GROUP,
        _REGISTRY_DEF_GROUP,
        GroupDefinition(
            name='Registry Data',
            dirname='registry_data',
            datagroups=(
                _USERS_GROUP,
                GroupDefinition(
                    name='Demographic Data',
                    dirname='demographic_data',
                    models=(
                        # Leave RDRFContexts before Patients, so that no
                        # default contexts are created on import. This works
                        # because there is no FK from RDRFContext to Patient
                        'rdrf.RDRFContext',
                        'patients.Patient',
                        'rdrf.QuestionnaireResponse',
                        # TODO is it ok to include all Doctors or should we include only
                        # referred Doctors?
                        'patients.Doctor',
                        'patients.PatientDoctor',
                        'patients.ClinicianOther',
                        'patients.ParentGuardian',
                        'patients.PatientAddress',
                        'patients.PatientConsent',
                        'patients.PatientRelative',
                        'patients.ConsentValue',
                         # TODO is it ok to include all Notifications?
                        # They aren't linked to registry, and from and to are not FKs
                        'rdrf.Notification',
                        'rdrf.EmailNotification',
                        'rdrf.EmailNotificationHistory',
                    )),
                GroupDefinition(
                    name='Clinical Data',
                    dirname='clinical_data',
                    models=(
                        'rdrf.CDEFile',
                        'rdrf.ClinicalData',
                    )),
            )
        ),
    )
)
