# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

# RDR-1296 introduces the init management command that can be used to load
# data into new RDRF installations. Therefore, migrations that load data
# automatically will be disabled from now.
# We're keeping the migration so that it doesn't confuse existing installations
# that already applied them, but disabling the actual loading of the data.


def load_groups(apps, schema_editor):
    # call_command("loaddata", "initial_groups.json", exceptiononerror=True)
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0002_auto_20150828_1519'),
    ]

    operations = [
        migrations.RunPython(load_groups)
    ]
