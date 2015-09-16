# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0007_auto_20150915_1546'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patient',
            name='maiden_name',
            field=models.CharField(max_length=100, null=True, verbose_name=b'Maiden name (if applicable)', blank=True),
        ),
    ]
