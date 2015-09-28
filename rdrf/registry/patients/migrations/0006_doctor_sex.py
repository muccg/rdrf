# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0005_auto_20150915_1518'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='sex',
            field=models.CharField(blank=True, max_length=1, null=True, choices=[(b'1', b'Male'), (b'2', b'Female'), (b'3', b'Indeterminate')]),
        ),
    ]
