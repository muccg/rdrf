# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0002_auto_20150828_1519'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parentguardian',
            name='gender',
            field=models.CharField(max_length=1, choices=[(b'M', b'Male'), (b'F', b'Female'), (b'I', b'Indeterminate')]),
        ),
    ]
