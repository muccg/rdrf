# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations
from django.core.management import call_command


def load_genes(apps, schema_editor):
    call_command("loaddata", "initial_genes.json", exceptiononerror=True)


def load_labs(apps, schema_editor):
    call_command("loaddata", " genetic.laboratories.json", exceptiononerror=True)


def load_techniques(apps, schema_editor):
    call_command("loaddata", "technique.json", exceptiononerror=True)


class Migration(migrations.Migration):

    dependencies = [
        ('genetic', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_genes),
        migrations.RunPython(load_labs),
        migrations.RunPython(load_techniques),
    ]
