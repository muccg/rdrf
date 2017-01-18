# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-12 03:11
from __future__ import unicode_literals

from django.db import migrations, models
import rdrf.jsonb


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0038_remove_dummy'),
    ]

    operations = [
        migrations.CreateModel(
            name='Modjgo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registry_code', models.CharField(db_index=True, max_length=10)),
                ('collection', models.CharField(choices=[('cdes', 'cdes'), ('history', 'history'), ('progress', 'progress'), ('registry_specific_patient_data', 'registry_specific_patient_data')], db_index=True, max_length=50)),
                ('data', rdrf.jsonb.DataField(default=dict)),
            ],
        ),
    ]
