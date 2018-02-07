# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def make_positive(apps, schema_editor):
    RegistryForm = apps.get_model("rdrf", "RegistryForm")
    RegistryForm.objects.filter(position__lt=0).update(position=0)


def do_nothing(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0036_auto_20161026_1853'),
    ]

    operations = [
        migrations.RunPython(make_positive, do_nothing),
        migrations.AlterField(
            model_name='registryform',
            name='position',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
