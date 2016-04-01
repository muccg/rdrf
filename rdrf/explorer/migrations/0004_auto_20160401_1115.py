# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('explorer', '0003_auto_20151110_1435'),
    ]

    operations = [
        migrations.AlterField(
            model_name='query',
            name='mongo_search_type',
            field=models.CharField(default=b'C', max_length=1, choices=[(b'C', b'Current'), (b'L', b'Longitudinal'), (b'M', b'Mixed')]),
        ),
    ]
