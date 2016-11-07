# -*- coding: utf-8 -*-


from django.db import migrations, models

forward_map = {
    "M": "1",
    "F": "2",
    "I": "3"
}

backward_map = {
    "1": "M",
    "2": "F",
    "3": "I"
}


def update_gender(pg, forward=True):
    if forward:
        m = forward_map
    else:
        m = backward_map

    updated_value = m.get(pg.gender, None)
    if updated_value:
        pg.gender = updated_value
        pg.save()
    else:
        print("Could not map ParentGuardian gender for %s" % pg)


def forwards_func(apps, schema_editor):
    ParentGuardian = apps.get_model("patients", "ParentGuardian")
    for pg in ParentGuardian.objects.all():
        update_gender(pg)


def backwards_func():
    ParentGuardian = apps.get_model("patients", "ParentGuardian")
    for pg in ParentGuardian.objects.all():
        update_gender(pg, forward=False)


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0015_auto_20160711_2209'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parentguardian',
            name='gender',
            field=models.CharField(max_length=1, choices=[(
                '1', 'Male'), ('2', 'Female'), ('3', 'Indeterminate')]),
        ),
        migrations.RunPython(
            forwards_func,
            backwards_func)
    ]
