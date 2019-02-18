from rdrf.models.definition import models
from registry.patients import models as patientmodels
from explorer import models as explorermodels
from registry.groups import models as groupmodels
from .catalogue import ModelExporterCatalogue
from .exporters import ModelExporter


class ModelExporterFilteredByRegistry(ModelExporter):

    @property
    def queryset(self):
        return self.model.objects.filter(registry__code=self.exporter_context['registry_code'])


class ModelExporterFilteredByRegistryCode(ModelExporter):

    @property
    def queryset(self):
        return self.model.objects.filter(registry_code=self.exporter_context['registry_code'])


class ModelExporterFilteredByPatient(ModelExporter):

    @property
    def queryset(self):
        return self.model.objects.filter(
            patient__rdrf_registry__code=self.exporter_context['registry_code'])


# Catalogue with generic exporters
catalogue = ModelExporterCatalogue()

# Registry specific exporters. Querysets filtered by registry code.
registry_catalogue = ModelExporterCatalogue()


class RegistryExporter(ModelExporter):

    @property
    def queryset(self):
        return self.model.objects.filter(code=self.exporter_context['registry_code'])


class SectionExporter(ModelExporter):

    @staticmethod
    def get_sections(registry_code):
        registry = models.Registry.objects.get(code=registry_code)
        for form in models.RegistryForm.objects.filter(registry=registry):
            for section_model in form.section_models:
                yield section_model
        if registry.patient_data_section is not None:
            yield registry.patient_data_section
        for section_code in registry.generic_sections:
            yield models.Section.objects.get(code=section_code)

    @property
    def queryset(self):
        return self.get_sections(self.exporter_context['registry_code'])


class CommonDataElementExporter(ModelExporter):

    @property
    def queryset(self):
        sections = SectionExporter.get_sections(self.exporter_context['registry_code'])
        all_unique_cdes_in_sections = set.union(*[set(s.cde_models) for s in sections])
        for cde in all_unique_cdes_in_sections:
            yield cde


class ConsentQuestionExporter(ModelExporter):

    @property
    def queryset(self):
        return self.model.objects.filter(
            section__registry__code=self.exporter_context['registry_code'])


class EmailNotificationHistoryExporter(ModelExporter):

    @property
    def queryset(self):
        return self.model.objects.filter(
            email_notification__registry__code=self.exporter_context['registry_code'])


class WizardExporter(ModelExporter):
    @property
    def queryset(self):
        return self.model.objects.filter(registry=self.exporter_context['registry_code'])


class ContextFormGroupItemExporter(ModelExporter):
    @property
    def queryset(self):
        return self.model.objects.filter(
            context_form_group__registry__code=self.exporter_context['registry_code'])


class CustomUserExporter(ModelExporter):
    @property
    def queryset(self):
        # Return only users that are associated with the registry we're exporting
        # In addition the users registries and working groups are filtered to include only the
        # registry we export and working groups in the registry we export
        # Otherwise when importing the users they will fail if the other registries/working groups
        # the user refers to don't exist
        registry_code = self.exporter_context['registry_code']
        for user in self.model.objects.filter(registry__code=registry_code):
            user.registry.set(models.Registry.objects.filter(code=registry_code))
            user.working_groups.set(groupmodels.WorkingGroup.objects.filter(
                registry__code=registry_code))
            yield user


class PatientExporter(ModelExporter):

    @property
    def queryset(self):
        return self.model.objects.filter(
            rdrf_registry__code=self.exporter_context['registry_code'])


registry_catalogue.register(models.Registry, RegistryExporter)
registry_catalogue.register(groupmodels.WorkingGroup, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.RegistryForm, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.Section, SectionExporter)
registry_catalogue.register(models.CommonDataElement, CommonDataElementExporter)
registry_catalogue.register(models.ConsentSection, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.ConsentQuestion, ConsentQuestionExporter)
registry_catalogue.register(models.DemographicFields, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.EmailNotification, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.EmailNotificationHistory, EmailNotificationHistoryExporter)
registry_catalogue.register(models.CdePolicy, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.Wizard, WizardExporter)
registry_catalogue.register(models.ContextFormGroup, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.ContextFormGroupItem, ContextFormGroupItemExporter)

registry_catalogue.register(groupmodels.CustomUser, CustomUserExporter)
registry_catalogue.register(patientmodels.Patient, PatientExporter)
registry_catalogue.register(patientmodels.ParentGuardian, ModelExporterFilteredByPatient)
registry_catalogue.register(patientmodels.PatientDoctor, ModelExporterFilteredByPatient)
registry_catalogue.register(patientmodels.ClinicianOther, ModelExporterFilteredByPatient)
registry_catalogue.register(patientmodels.PatientAddress, ModelExporterFilteredByPatient)
registry_catalogue.register(patientmodels.PatientConsent, ModelExporterFilteredByPatient)
registry_catalogue.register(patientmodels.PatientRelative, ModelExporterFilteredByPatient)
registry_catalogue.register(patientmodels.ConsentValue, ModelExporterFilteredByPatient)
registry_catalogue.register(models.RDRFContext, ModelExporterFilteredByRegistry)
registry_catalogue.register(models.QuestionnaireResponse, ModelExporterFilteredByRegistry)

registry_catalogue.register(models.CDEFile, ModelExporterFilteredByRegistryCode)
registry_catalogue.register(models.ClinicalData, ModelExporterFilteredByRegistryCode)

registry_catalogue.register(explorermodels.Query, ModelExporterFilteredByRegistry)
