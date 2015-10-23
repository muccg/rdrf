# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0003_auto_20150831_1321'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='rdrf_username',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='working_groups',
            field=models.ManyToManyField(related_name='working_groups', to='groups.WorkingGroup'),
        ),
    ]
