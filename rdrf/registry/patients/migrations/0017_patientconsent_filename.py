# -*- coding: utf-8 -*-


from django.db import migrations
import os.path


def default_filename(apps, schema_editor):
    PatientConsent = apps.get_model("patients", "PatientConsent")
    for pc in PatientConsent.objects.all():
        if not pc.filename:
            pc.filename = os.path.basename(pc.form.name)
            pc.save()


def clear_filename(apps, schema_editor):
    PatientConsent = apps.get_model("patients", "PatientConsent")
    PatientConsent.objects.all().update(filename="")


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0016_patientconsent_filename'),
    ]

    operations = [
        migrations.RunPython(default_filename, clear_filename),
    ]
