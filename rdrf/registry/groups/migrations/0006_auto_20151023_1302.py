# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0005_auto_20151023_1253'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='rdrf_username',
            field=models.CharField(unique=True, max_length=255),
        ),
    ]
