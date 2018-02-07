# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0036_auto_20161026_1853'),
    ]

    operations = [
        migrations.AddField(
            model_name='cdefile',
            name='cde_code',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AddField(
            model_name='cdefile',
            name='form_name',
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name='cdefile',
            name='registry_code',
            field=models.CharField(default='', max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cdefile',
            name='section_code',
            field=models.CharField(blank=True, max_length=100),
        )

    ]
