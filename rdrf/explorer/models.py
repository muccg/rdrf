from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RegistryForm
from rdrf.models.definition.models import RDRFContext
from rdrf.models.definition.models import Section
from rdrf.models.definition.models import CommonDataElement
from rdrf.helpers.utils import parse_iso_date
from registry.patients.models import Patient

import logging

logger = logging.getLogger(__name__)

class FieldValue(models.Model):
    """
    Used for reporting
    """
    registry = models.ForeignKey(Registry)
    patient = models.ForeignKey(Patient)
    context = models.ForeignKey(RDRFContext)
    form = models.ForeignKey(RegistryForm)
    section = models.ForeignKey(Section)
    index = models.IntegerField(default=0)
    cde = models.ForeignKey(CommonDataElement)
    raw_value = models.TextField(blank=True,null=True)
    display_value = models.TextField(blank=True,null=True,default="")
    username = models.TextField(blank=True,null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    column_name = models.CharField(max_length=80, blank=True, null=True)

    class Meta:
        # the "path" to a value for a giveb
        unique_together = ("registry", "patient","context", "form","section","index","cde")

    @classmethod
    def get(klass, registry_model, patient_model, context_model,form_model, section_model, cde_model, index=0):
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
        model = klass.get(registry_model, patient_model, context_model, form_model, section_model, cde_model,index)
        if model is not None:
            if display:
                return model.display_value
            else:
                return model.raw_value

    @classmethod
    def put(klass, registry_model, patient_model, context_model, form_model, section_model, cde_model, index, value):
        model, _ = klass.objects.get_or_create(registry=registry_model,
                                               patient=patient_model,
                                               context=context_model,
                                               form=form_model,
                                               section=section_model,
                                               cde=cde_model,
                                               index=index)

        model.raw_value = str(value)
        if cde_model.pv_group:
            # range
            model.display_value = cde_model.get_display_value(value)
        else:
            model.display_value = str(value)

        model.save()
        logger.debug("field value put %s value = %s" % (model, value))

    def __str__(self):
        return "registry %s patient %s context %s form %s section %s cde %s index %s" % (self.registry.code,
                                                                                                  self.patient,
                                                                                                  self.context.id,
                                                                                                  self.form.name,
                                                                                                  self.section.code,
                                                                                                  self.cde.code,
                                                                                                  self.index)
    


    def get_column_name(self):
        # column name for report
        if self.cde.pv_group:
            # multisection so include index + 1
            name = "column_%s_%s_%s_%s" % (self.form.pk,
                                           self.section.pk,
                                           self.cde.code,
                                           self.index + 1)
        else:
            name = "column_%s_%s_%s" % (self.form.pk,
                                        self.section.pk,
                                        self.cde.code)

        return name

    def get_typed_value(self):
        datatype = self.cde.datatype.strip().lower()
        if datatype == 'integer':
            try:
                return int(self.raw_value)
            except:
                return None
        elif datatype in ['float','decimal','number','numeric']:
            try:
                return float(self.raw_value)
            except:
                return None
        elif datatype in ['boolean','bool']:
            try:
                return bool(self.raw_value)
            except:
                return None
        elif datatype == 'file':
            return 'file'
        elif datatype in ['date', 'datetime']:
            try:
                return parse_iso_date(self.raw_value)
            except:
                return None
        else:
            return self.raw_value

    def get_report_value(self):
        if self.cde.pv_group:
            return self.cde.get_display_value(self.raw_value)
        else:
            try:
                return self.get_typed_value()
            except ValueError:
                return None
        
        



class Query(models.Model):
    MONGO_SEARCH_TYPES = (
        ('C', 'Current'),
        ('L', 'Longitudinal'),
        ('M', 'Mixed'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    registry = models.ForeignKey(Registry)
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
        return reverse('explorer_query', kwargs={'query_id': self.pk})

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
