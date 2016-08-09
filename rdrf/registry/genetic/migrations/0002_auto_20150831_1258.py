# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models, migrations
from django.core.management import call_command

# RDR-1296 introduces the init management command that can be used to load
# data into new RDRF installations. Therefore, migrations that load data
# automatically will be disabled from now.
# We're keeping the migration so that it doesn't confuse existing installations
# that already applied them, but disabling the actual loading of the data.


def load_genes(apps, schema_editor):
    # call_command("loaddata", "initial_genes.json", exceptiononerror=True)
    pass


def load_labs(apps, schema_editor):
    # call_command("loaddata", " genetic.laboratories.json", exceptiononerror=True)
    pass


def load_techniques(apps, schema_editor):
    # call_command("loaddata", "technique.json", exceptiononerror=True)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('genetic', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_genes),
        migrations.RunPython(load_labs),
        migrations.RunPython(load_techniques),
    ]
