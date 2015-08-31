# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management import call_command


def load_groups(apps, schema_editor):
    call_command("loaddata", "initial_groups.json", exceptiononerror=True)


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0002_auto_20150828_1519'),
    ]

    operations = [
        migrations.RunPython(load_groups)
    ]
