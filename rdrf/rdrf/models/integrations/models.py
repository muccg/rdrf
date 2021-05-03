from django.db import models
from django.core.exceptions import ValidationError
import logging
from rdrf.models.definition.models import Registry
from registry.patients.models import Patient

logger = logging.getLogger(__name__)


class IntegrationError(Exception):
    pass


class IntegrationConversionError(IntegrationError):
    pass


class IntegrationFieldMissing(Exception):
    pass


class Integration(models.Model):
    EXTERNAL_SYSTEMS = (('dummy', 'Dummy'),
                        ('webpas', 'Web Pas'),
                        ('isoft', 'ISoft ICM'),
                        ('genie', 'Genie'),
                        ('qool', 'QOOL'),
                        ('wacr', 'WA Cancer Registry'),
                        ('coca', 'CoCa'),
                        ('ultralis', 'Ultra/LIS'),
                        ('mosaiq', 'Mosaiq'),
                        ('impax', 'IMPAX'),
                        ('ipharmacy', 'IPharmacy'),
                        ('pcor', 'PCOR'))

    registry = models.ForeignKey(Registry)
    system = models.CharField(max_length=100, choices=EXTERNAL_SYSTEMS)
    config = models.TextField(blank=True)  # json

    def get_module_function(self, function_name):
        """
        Look for a function registered as an integration function
        in the related integration module.
        If it doesn't exist return None.

        """
        try:
            system_integration_module_name = f"rdrf.services.io.integrations.{self.system}"
            system_integration_module = __import__(system_integration_module_name)
        except ImportError:
            return None

        if hasattr(system_integration_module, function_name):
            func = getattr(system_integration_module, function_name)
            if hasattr(func, "integration_function") and func.integration_function:
                if callable(func):
                    return func

    def receive(self, packet):
        # assume data is sent as a set of packets of some type
        update_data = self._process_packet(packet)
        self.update_rdrf(update_data)

    def _process_packet(self, packet):
        update_data = []
        for patient in self.get_patients(packet):
            patient_data = {}
            for field in self.fields:
                try:
                    raw_value = field.get_value(patient, packet)
                    converted_value = field.convert(raw_value)
                    patient_data[field] = converted_value
                except IntegrationConversionError as ice:
                    logger.error("Error processing incoming field")
                except ValidationError as verr:
                    logger.error("Error processing incoming field")
            updated_data.append((patient, patient_data))
        return update_data

    def get_patients(self, packet):
        return Patient.objects.filter(rdrf_registry__in=[self.registry])


class IntegrationField(models.Model):
    integration = models.ForeignKey(Integration, related_name='fields')
    form_name = models.CharField(max_length=80, blank=True)
    section_code = models.CharField(max_length=100, blank=True)
    cde_code = models.CharField(max_length=30, blank=True)
    config = models.TextField()
    external_code = models.CharField(max_length=100)

    def get_value(self, patient, packet):
        patient_integration = self.integration.get_patient_integration(patient)
        patient_id = patient_integration.external_id

        get_field_func_name = f"get_field_{self.external_code}"
        get_field = self.integration.get_module_function(get_field_func_name)

        conversion_function_name = f"convert_field_{self.external_code}"
        conversion_function = self.integration.get_module_function(conversion_function_name)

        if get_field:
            raw_value = get_field(patient_id, self.external_id, packet)
            if conversion_function:
                value = conversion_function(raw_value)
                return converted_value
            else:
                value = raw_value

            if self.validity_check(value):
                return value
            else:
                raise IntegrationError("field value not sane")

    def validity_check(self, value):
        validation_funcs = self.get_validation_functions()
        errors = []

        for validation_func in validation_funcs:
            try:
                validation_func(value)
            except ValidationError as verr:
                errors.append(verr.message)

        if len(errors) == 0:
            return True
        else:
            return False

    def get_validation_functions(self):
        """
        return the associated RDRF field validation functions
        """
        from rdrf.forms.dynamic import validation
        cde_model = CommonDataElement.objects.get(code=self.cde_code)
        validator == validation.ValidatorFactory(cde_model)

        return validator.create_validators()

