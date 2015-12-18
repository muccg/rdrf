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
        self.registry_codes = self._get_registry_codes()

    def _get_registry_codes(self):
        Registry = self.apps.get_model("rdrf", 'Registry')
        codes = [r.code for r in Registry.objects.all()]
        print "found codes: %s" % ",".join(codes)
        return codes

    def _get_patient_model(self, patient_record):
        patient_id = None
        try:
            patient_id = patient_record.get("django_id", None)
            Patient = self.apps.get_model("registry.patients", "Patient")
            patient_model = Patient.objects.get(pk=patient_id)
            return patient_model
        except Exception, ex:
            print "Error getting patient model for %s: %s" % (patient_id, ex)
            return None

    def _get_registry_model(self, registry_code):
        Registry = self.apps.get_model("rdrf", 'Registry')
        return Registry.objects.get(code-registry_code)

    def _create_default_context(self, registry_model, patient_model):
        from rdrf.contexts_api import RDRFContextManager
        rdrf_context_manager = RDRFContextManager(registry_model)
        RDRFContext = self.apps.get_model("rdrf", "RDRFContext")
        patient_contexts = [c for c in RDRFContext.objects.filter(content_type=patient_content_type,
                                                                  object_id=patient_model.pk,
                                                                  registry=registry_model)]

        num_contexts = len(patient_contexts)

        if num_contexts == 0:
            default_context = rdrf_context_manager.create_context(patient_model, "default")
            default_context.save()
            print "created default context for patient %s" % patient_model
            return default_context
        else:
            print "There are already %s contexts for patient %s in registry %s" % (num_contexts,
                                                                                   patient_model.pk,
                                                                                   registry_model.code)

    def _update_record(self, registry, patient_record, context_id):
        mongo_id = patient_record['_id']
        patient_record["context_id"] = context_id
        registry["cdes"].update({'_id': mongo_id}, {"$set": patient_record}, upsert=False)
        print "Updated patient %s mongo record with context_id %s" % (patient_record["django_id"],
                                                                      context_id)



    def fix_registries(self):
        for registry_code in self.registry_codes:
            registry = self.client[mongo_db_name(registry_code)]
            registry_model = self._get_registry_model(registry_code)

            for patient_record in registry["cdes"].find({"django_model": "Patient"}):
                if "context_id" not in patient_record:
                    patient_model = self._get_patient_model(patient_record)
                    default_context_model = self._create_default_context(registry_model, patient_model)
                    if default_context_model is not None:
                        self._update_record(registry, patient_record, default_context_model.pk)
                    else:
                        print ""


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
            field=models.CharField(max_length=80, choices=[(b'initial', b'initial'), (b'testing', b'testing'), (b'1.0.17', b'populate context_id on all patient records')]),
        ),
        migrations.RunPython(forwards_func, backwards_func)
    ]
