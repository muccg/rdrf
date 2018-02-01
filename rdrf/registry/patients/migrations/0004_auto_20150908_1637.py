# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0003_auto_20150908_1410'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient', name='living_status', field=models.CharField(
                default='Alive', max_length=80, choices=[
                    ('Alive', 'Living'), ('Deceased', 'Deceased')]), ), migrations.AlterField(
            model_name='patientrelative', name='sex', field=models.CharField(
                max_length=1, choices=[
                    ('1', 'Male'), ('2', 'Female'), ('3', 'Indeterminate')]), ), ]
