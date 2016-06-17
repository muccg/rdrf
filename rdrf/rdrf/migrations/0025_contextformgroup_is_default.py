# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0024_auto_20160223_1344'),
    ]

    operations = [
        migrations.AddField(
            model_name='contextformgroup',
            name='is_default',
            field=models.BooleanField(default=False),
        ),
    ]
