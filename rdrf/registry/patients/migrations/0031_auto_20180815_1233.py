# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-08-15 12:33
from __future__ import unicode_literals

from django.db import migrations, models
import registry.patients.models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0030_auto_20180813_1606'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patientconsent',
            name='form',
            field=models.FileField(blank=True, null=True, storage=registry.patients.models.PatientConsentStorage(), upload_to='consents', verbose_name='Consent form'),
        ),
    ]
