# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0008_auto_20150916_1518'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parentguardian',
            name='gender',
            field=models.CharField(max_length=1, choices=[(b'M', b'Male'), (b'F', b'Female'), (b'I', b'Indeterminate')]),
        ),
    ]
