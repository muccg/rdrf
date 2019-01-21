from django.db import models
from django.urls import reverse
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import RDRFContext
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.helpers.utils import parse_iso_date
from registry.patients.models import Patient
import json

import logging

logger = logging.getLogger(__name__)

class FieldValue(models.Model):
    """
    Used for reporting
    """
    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    context = models.ForeignKey(RDRFContext, on_delete=models.CASCADE)
    form = models.ForeignKey(RegistryForm, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, on_delete=models.CASCADE)
    index = models.IntegerField(default=0)
    cde = models.ForeignKey(CommonDataElement, on_delete=models.CASCADE)
    raw_value = models.TextField(blank=True, null=True)
    display_value = models.TextField(blank=True, null=True, default="")
    username = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    column_name = models.CharField(max_length=80, blank=True, null=True)
    datatype = models.CharField(max_length=80, default='string')
    is_range = models.BooleanField(default=False)
    raw_integer = models.IntegerField(null=True, blank=True)
    raw_float = models.FloatField(null=True, blank=True)
    file_name = models.TextField(null=True, blank=True)
    raw_date = models.DateField(null=True, blank=True)
    raw_boolean = models.NullBooleanField(null=True, blank=True)

    class Meta:
        # the "path" to a value for a giveb
        unique_together = ("registry", "patient", "context", "form", "section", "index", "cde")

    @classmethod
    def get(klass, registry_model, patient_model, context_model, form_model, section_model, cde_model, index=0):
        try:
            return klass.objects.get(registry=registry_model,
                                     patient=patient_model,
                                     context=context_model,
                                     form=form_model,
                                     section=section_model,
                                     cde=cde_model,
                                     index=index)
        except klass.DoesNotExist:
            return None

    @classmethod
    def get_value(klass, registry_model, patient_model, context_model, form_model, section_model, cde_model, index=0, display=False):
        model = klass.get(registry_model, patient_model, context_model, form_model, section_model, cde_model, index)
        if model is not None:
            if display:
                return model.display_value
            else:
                return model.raw_value

    @classmethod
    def put(klass, registry_model, patient_model, context_model, form_model, section_model, cde_model, index, value):
        datatype = cde_model.datatype.strip().lower()
        model, _ = klass.objects.get_or_create(registry=registry_model,
                                               patient=patient_model,
                                               context=context_model,
                                               form=form_model,
                                               section=section_model,
                                               cde=cde_model,
                                               index=index)

        model.datatype = model.set_datatype(datatype)
        model.is_range = True if cde_model.pv_group else False
        model.column_name = model.get_column_name(form_model,
                                                  section_model,
                                                  cde_model,
                                                  index)
        if value is None:
            model.save()
            return

        if datatype == 'string':
            try:
                model.raw_value = str(value)
            except BaseException:
                pass
        elif cde_model.pv_group:
            model.display_value = cde_model.get_display_value(value)
        elif datatype in ['integer', 'int', 'ineger']:
            try:
                model.raw_integer = int(value)
            except TypeError:
                pass
            except ValueError:
                pass
        elif datatype in ['boolean', 'bool']:
            try:
                model.raw_boolean = bool(value)
            except BaseException:
                pass
        elif datatype in ['float', 'numeric', 'decimal']:
            try:
                model.raw_float = float(value)
            except TypeError:
                pass
            except ValueError:
                pass
        elif datatype == 'date':
            try:
                model.raw_date = parse_iso_date(value)
            except BaseException:
                pass
        elif datatype == 'file':
            try:
                model.file_name = value.get("file_name", None)
            except BaseException:
                pass
        else:
            try:
                model.raw_value = str(value)
            except BaseException:
                pass

        model.save()

    def set_datatype(self, datatype):
        if datatype in ['string', 'striing']:
            return 'string'
        if datatype in ['integer', 'ineger']:
            return 'integer'
        if datatype in ['float', 'decimal', 'number']:
            return 'float'
        if datatype in ['date', 'datetime']:
            return 'date'
        if datatype in ['boolean', 'bool']:
            return 'boolean'
        if datatype in ['file']:
            return 'file'
        if datatype in ['range']:
            return 'range'
        if datatype in ['calculated']:
            return 'calculated'
        return 'string'

    def get_calculated_value(self):
        try:
            return float(self.raw_value)
        except BaseException:
            pass
        return self.raw_value

    def __str__(self):
        return "registry %s patient %s context %s form %s section %s cde %s index %s" % (self.registry.code,
                                                                                         self.patient,
                                                                                         self.context.id,
                                                                                         self.form.name,
                                                                                         self.section.code,
                                                                                         self.cde.code,
                                                                                         self.index)

    def get_column_name(self, form_model, section_model, cde_model, index):
        # column name for report
        if section_model.allow_multiple:
            # multisection so include index + 1
            name = "column_%s_%s_%s_%s" % (form_model.pk,
                                           section_model.pk,
                                           cde_model.code,
                                           index + 1)
        else:
            name = "column_%s_%s_%s" % (form_model.pk,
                                        section_model.pk,
                                        cde_model.code)

        return name

    def get_typed_value(self):
        #'text', 'email', 'range', 'integer',
        #'file', 'string', 'float', 'String', 'date', 'striing',
        # 'calculated', 'Integer', 'Ineger', 'textarea', 'boolean'}

        datatype = self.cde.datatype.strip().lower()
        if datatype in ['text', 'email', 'string', 'textarea']:
            return self.raw_value

        if datatype in ['integer', 'ineger']:
            try:
                return int(self.raw_value)
            except BaseException:
                return None
        elif datatype in ['float', 'decimal', 'number', 'numeric']:
            try:
                return float(self.raw_value)
            except BaseException:
                return None
        elif datatype in ['boolean', 'bool']:
            try:
                return bool(self.raw_value)
            except BaseException:
                return None
        elif datatype == 'file':
            try:
                if not self.raw_value:
                    return None
                file_name = json.loads(self.raw_value)["file_name"]
                logger.debug("got a file name = %s" % file_name)
                return file_name
            except Exception as ex:
                logger.debug("error getting filename: %s" % ex)
                return None
        elif datatype in ['date', 'datetime']:
            try:
                return parse_iso_date(self.raw_value)
            except BaseException:
                return None
        elif datatype == 'calculated':
            try:
                return float(self.raw_value)
            except ValueError:
                return self.raw_value

        else:
            return self.raw_value

    def get_report_value(self):
        if self.cde.pv_group:
            return self.display_value
        else:
            try:
                typed_value = self.get_typed_value()
                return typed_value

            except ValueError as ex:
                return None
            except Exception as ex:
                return None


class Query(models.Model):
    MONGO_SEARCH_TYPES = (
        ('C', 'Current'),
        ('L', 'Longitudinal'),
        ('M', 'Mixed'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    registry = models.ForeignKey(Registry, on_delete=models.CASCADE)
    access_group = models.ManyToManyField(Group)

    mongo_search_type = models.CharField(max_length=1, choices=MONGO_SEARCH_TYPES, default='C')

    collection = models.CharField(max_length=255, default="cdes")
    criteria = models.TextField(blank=True, null=True)
    projection = models.TextField(blank=True, null=True)
    aggregation = models.TextField(blank=True, null=True)

    sql_query = models.TextField()
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # max number of multisection items to show in datatable
    max_items = models.IntegerField(default=3)

    def get_absolute_url(self):
        return reverse('rdrf:explorer_query', kwargs={'query_id': self.pk})

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'Queries'

    def __str__(self):
        return str(self.title)

    def has_view(self):
        return self.mongo_search_type in ['C', 'L']

    def clean(self):
        if self.mongo_search_type == "M":
            errors = self._get_mixed_query_errors()
            if len(errors) > 0:
                error_string = ",".join(errors)
                raise ValidationError("Report Config Errors: %s" % error_string)

    def _get_mixed_query_errors(self):
        import json
        errors = []
        try:
            data = json.loads(self.sql_query)
            static_sheets = data["static_sheets"]
            for sheet in static_sheets:
                sheet_name = sheet["name"]
                columns = sheet["columns"]
                for column in columns:
                    if not isinstance(column, str):
                        errors.append(
                            "columns in sheet %s not all strings: %s" %
                            (sheet_name, column))

        except ValueError as ve:
            errors.append("JSON malformed: %s" % ve)
        except KeyError as ke:
            errors.append("key error: %s" % ke)
        return errors
