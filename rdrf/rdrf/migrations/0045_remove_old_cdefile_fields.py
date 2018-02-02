# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0044_cdefile_data_migration'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cdefile',
            name='cde',
        ),
        migrations.RemoveField(
            model_name='cdefile',
            name='form',
        ),
        migrations.RemoveField(
            model_name='cdefile',
            name='registry',
        ),
        migrations.RemoveField(
            model_name='cdefile',
            name='section',
        )

    ]
