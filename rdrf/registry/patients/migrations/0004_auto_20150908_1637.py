# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0003_auto_20150908_1410'),
    ]

    operations = [
        migrations.AddField(
            model_name='patient',
            name='living_status',
            field=models.CharField(default=b'Alive', max_length=80, choices=[(b'Alive', b'Living'), (b'Deceased', b'Deceased')]),
        ),
        migrations.AlterField(
            model_name='patientrelative',
            name='sex',
            field=models.CharField(max_length=1, choices=[(b'1', b'Male'), (b'2', b'Female'), (b'3', b'Indeterminate')]),
        ),
    ]
