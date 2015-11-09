# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0006_auto_20151105_1422'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailnotification',
            name='description',
            field=models.CharField(max_length=100, choices=[(b'other-clinician', b'Other Clinician'), (b'new-patient', b'New Patient Registered')]),
        ),
    ]
