# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations
from rdrf.helpers.migration_utils import ClinicalDBRunPython

mongo_django = undjango_mongo = None


def copy_collections(apps, schema_editor):
    Modjgo = apps.get_model("rdrf", "Modjgo")
    print("got Modjgo okay")
    Registry = apps.get_model("rdrf", "Registry")
    if mongo_django:
        mongo_django(Modjgo, Registry.objects.all())

# note: migration is not fully reversable. it just removes the flag
# which says the mongo document was migrated.


def uncopy_collections(apps, schema_editor):
    Modjgo = apps.get_model("rdrf", "Modjgo")
    Registry = apps.get_model("rdrf", "Registry")
    if undjango_mongo:
        undjango_mongo(Modjgo, Registry.objects.all())


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0039_modjgo'),
    ]

    operations = [
        ClinicalDBRunPython(copy_collections, uncopy_collections),
    ]
