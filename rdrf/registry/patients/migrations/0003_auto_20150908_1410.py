# -*- coding: utf-8 -*-


from django.db import migrations


def fix_patient_relative_sex(apps, schema_editor):
    patient_relative_model_class = apps.get_model("patients", "PatientRelative")
    for patient_relative in patient_relative_model_class.objects.all():
        if patient_relative.sex == "M":
            patient_relative.sex = "1"
        elif patient_relative.sex == "F":
            patient_relative.sex = "2"
        elif patient_relative.sex == "X":
            patient_relative.sex = "3"

        try:
            patient_relative.save()
        except Exception as ex:
            print("could not update PatientRelative pk=%s: %s" % (patient_relative.pk, ex))


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_auto_20150828_1519'),
    ]

    operations = [
        migrations.RunPython(fix_patient_relative_sex),
    ]
