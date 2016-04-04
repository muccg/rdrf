# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rdrf', '0018_auto_20160223_1709'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailnotification',
            name='disabled',
            field=models.BooleanField(default=False),
        ),
    ]
