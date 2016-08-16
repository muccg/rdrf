# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

from rdrf.mongo_client import construct_mongo_client
from rdrf.utils import mongo_db_name

from registry.patients.models import Patient


class MongoContextFixer(object):

    def __init__(self, client, apps, schema_editor):
        self.client = client
        self.apps = apps
        self.schema_editor = schema_editor
        self.registry_klass = self._get_registry_class()
        self.registry_codes = self._get_registry_codes()

    def _get_registry_codes(self):
        #Registry = self.apps.get_model("rdrf", 'Registry')
        if self.registry_klass:
            codes = [r.code for r in self.registry_klass.objects.all()]
            print "found codes: %s" % ",".join(codes)
            return codes
        else:
            return []

    def _get_patient_model(self, patient_record):
        patient_id = None
        try:
            patient_id = patient_record.get("django_id", None)
            Patient = self._get_patient_class()
            try:
                patient_model = Patient.objects.get(pk=patient_id)
            except Patient.DoesNotExist:
                print "Patient ID %s in mongo does not exist in SQL DB" % patient_id
                return None
            return patient_model
        except Exception as ex:
            print "Error getting patient model for %s: %s" % (patient_id, ex)
            return None

    def _get_registry_class(self):
        #Registry = self.apps.get_model("rdrf", 'Registry')
        from rdrf.models import Registry
        return Registry

    def _get_patient_class(self):
        from registry.patients.models import Patient
        return Patient

    def _get_registry_model(self, registry_code):

        try:
            registry_model = self.registry_klass.objects.get(code=registry_code)
            return registry_model
        except self.registry_klass.DoesNotExist:
            return None

    def _create_default_context(self, registry_model, patient_model):
        from rdrf.contexts_api import RDRFContextManager
        rdrf_context_manager = RDRFContextManager(registry_model)

        default_rdrf_context = rdrf_context_manager.create_initial_context_for_new_patient(patient_model)
        print "registry_code %s patient id %s %s default context = %s %s" % (registry_model.code,
                                                                             patient_model.pk,
                                                                             patient_model,
                                                                             default_rdrf_context.pk,
                                                                             default_rdrf_context.display_name)
        return default_rdrf_context

    def _update_record(self, registry, patient_record, context_id):
        mongo_id = patient_record['_id']
        patient_record["context_id"] = context_id

        registry["cdes"].update({'_id': mongo_id}, {"$set": patient_record}, upsert=False)
        print "Updated patient %s mongo record with context_id %s" % (patient_record["django_id"],
                                                                      context_id)

    def fix_registries(self):
        self.registry_klass = self._get_registry_class()
        for registry_code in self.registry_codes:
            registry = self.client[mongo_db_name(registry_code)]
            registry_model = self._get_registry_model(registry_code)
            if registry_model is None:
                print "Registry %s not found - skipping" % registry_code
                continue

            for patient_record in registry["cdes"].find({"django_model": "Patient"}):
                if "context_id" not in patient_record:
                    patient_model = self._get_patient_model(patient_record)

                    if patient_model is None:
                        continue
                    try:
                        default_context_model = self._create_default_context(registry_model, patient_model)
                    except Exception as ex:
                        print "Error creating default context in %s for patient id %s: %s" % (registry_model,
                                                                                              patient_model.pk,
                                                                                              ex)
                        continue

                    if default_context_model is not None:
                        self._update_record(registry, patient_record, default_context_model.pk)
                    else:
                        print "default context None for patient %s - mongo not updated" % patient_model.pk


def forwards_func(apps, schema_editor):
    client = construct_mongo_client()
    context_fixer = MongoContextFixer(client, apps, schema_editor)
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
            field=models.CharField(
                max_length=80,
                choices=[
                    (b'initial',
                     b'initial'),
                    (b'testing',
                     b'testing'),
                    (b'1.0.17',
                     b'populate context_id on all patient records')]),
        ),
        migrations.RunPython(
            forwards_func,
            backwards_func)]
