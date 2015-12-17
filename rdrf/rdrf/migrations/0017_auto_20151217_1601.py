# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from rdrf.mongo_client import construct_mongo_client


class MongoContextFixer(object):
    def __init__(self, client):
        self.client = client
        self.registries = self._get_registries_to_check()

    def _get_registries_to_check(self):
        return []

    def _get_patient_model(self, registry, patient_record):
        pass

    def _create_default_context(self, registry, patient_model):
        pass

    def _update_record(self, registry, patient_record, context_id):
        pass

    def fix_registries(self):
        for registry in self.registries:
            for patient_record in registry["cdes"].find({"django_model": "Patient"}):
                if "context_id" not in patient_record:
                    patient_model = self._get_patient_model(registry, patient_record)
                    default_context_model = self._create_default_context(registry, patient_model)
                    self._update_record(registry, patient_record, default_context_model.pk)


def forwards_func(apps, schema_editor):
    client = construct_mongo_client()
    context_fixer = MongoContextFixer(client)
    context_fixer.fix_registries()


def backwards_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0016_auto_20151217_1339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mongomigrationdummymodel',
            name='version',
            field=models.CharField(max_length=80, choices=[(b'initial', b'initial'), (b'testing', b'testing'), (b'1.0.17', b'populate context_id on all patient records')]),
        ),
        migrations.RunPython(forwards_func, backwards_func)
    ]
