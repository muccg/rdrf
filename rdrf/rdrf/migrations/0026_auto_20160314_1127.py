# -*- coding: utf-8 -*-

from rdrf.models.definition.models import Registry
from rdrf.models.definition.models import RDRFContext
from django.contrib.contenttypes.models import ContentType

from django.db import migrations


def forward_func(apps, schema_editor):
    # no model changed so this should be ok
    patient_content_type = ContentType.objects.get(model='patient')
    for registry_model in Registry.objects.all():
        default_context_form_group = registry_model.default_context_form_group
        if default_context_form_group is not None:
            for context_model in RDRFContext.objects.filter(registry=registry_model,
                                                            content_type=patient_content_type,
                                                            context_form_group=None):
                context_model.context_form_group = default_context_form_group
                try:
                    context_model.save()
                    print("Updated RDRFContext %s context_form_group id = %s" %
                          (context_model.id, default_context_form_group.id))
                except Exception as ex:
                    print("Error updating RDRFContext %s: %s" % (context_model.id, ex))


def backward_func(apps, schema_editor):
    patient_content_type = ContentType.objects.get(model='patient')
    for registry_model in Registry.objects.all():
        default_context_form_group = registry_model.default_context_form_group
        if default_context_form_group is not None:
            for context_model in RDRFContext.objects.filter(
                    registry=registry_model,
                    content_type=patient_content_type,
                    context_form_group=default_context_form_group):
                context_model.context_form_group = None
                try:
                    context_model.save()
                    print("RDRFContext %s context_form_group set to null")
                except Exception as ex:
                    print("Error rolling back change to RDRFContext %s: %s" % (context_model.id,
                                                                               ex))


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0025_contextformgroup_is_default'),
    ]

    operations = [
    ]
