# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def set_codes(apps, schema_editor):
    CDEFile = apps.get_model("rdrf", "CDEFile")
    for f in CDEFile.objects.all():
        f.registry_code = f.registry.code
        f.form_name = f.form.name
        f.section_code = f.section.code
        f.cde_code = f.cde.code
        f.save()

def set_fks(apps, schema_editor):
    m = lambda model: apps.get_model("rdrf", model)
    CDEFile = m("CDEFile")
    for f in CDEFile.objects.all():
        f.registry = m("Registry").objects.get(code=f.registry_code)
        f.form = m("RegistryForm").objects.get(name=f.form_name)
        f.section = m("Section").objects.get(code=f.section_code)
        f.cde = m("CommonDataElement").objects.get(code=f.cde_code)
        f.save()

class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0036_auto_20161026_1853'),
    ]

    operations = [
        migrations.AddField(
            model_name='cdefile',
            name='cde_code',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='cdefile',
            name='form_name',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AddField(
            model_name='cdefile',
            name='registry_code',
            field=models.CharField(default='', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cdefile',
            name='section_code',
            field=models.CharField(blank=True, max_length=100),
        ),

        migrations.RunPython(set_codes, set_fks),

        migrations.RemoveField(
            model_name='cdefile',
            name='cde',
        ),
        migrations.RemoveField(
            model_name='cdefile',
            name='form',
        ),
        migrations.RemoveField(
            model_name='cdefile',
            name='registry',
        ),
        migrations.RemoveField(
            model_name='cdefile',
            name='section',
        ),
    ]
