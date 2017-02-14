# -*- coding: utf-8 -*-
from django.db import migrations

# will use TimeStripper here

def forwards(apps, schema_editor):
    pass

def backwards(apps, schema_editor):
    pass

                    

class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0045_remove_old_cdefile_fields'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards)
    ]
